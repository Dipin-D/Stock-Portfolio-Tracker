from datetime import date, timedelta
import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import numpy as np
import pandas as pd

from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .bayes.likelihoods import estimate_binary_likelihood
from .bayes.posterior import apply_evidence, estimate_signal_weight
from .bayes.priors import estimate_universe_prior
from .models import AppSettings, BacktestRun, EvidenceSnapshot, Portfolio, Stock, Stock_Group, StrategyRun, TradeLog
from .services.backtest_service import ensure_strategy_definitions
from .services.research_service import build_research_backtest_url
from .services.watchlist_service import get_momentum_watchlist
from .utils import PriceDataError, _cache_set, _make_cache_key, download_n_clean_data


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class BacktestChartTests(TestCase):
    def setUp(self):
        cache.clear()

    @staticmethod
    def sample_price_frame():
        return pd.DataFrame([
            {
                'Date': pd.Timestamp('2003-05-05').timestamp(),
                'Open': 10.0,
                'High': 11.0,
                'Low': 9.5,
                'Close': 10.5,
                'Volume': 1000,
                'sma_50': None,
                'sma_200': None,
            },
            {
                'Date': pd.Timestamp('2003-05-06').timestamp(),
                'Open': 10.5,
                'High': 11.5,
                'Low': 10.0,
                'Close': 11.0,
                'Volume': 1200,
                'sma_50': None,
                'sma_200': None,
            },
        ])

    @patch('my_app.views.download_n_clean_data')
    def test_backtest_shell_renders_without_downloading_market_data(self, mock_download):
        response = self.client.get(reverse('backtest'), {
            'ticker': 'AAPL',
            'start_date': '2003-05-05',
            'end_date': '2026-03-22',
            'autoload': '1',
            'analysis_mode': 'single',
            'prior_mode': 'universe',
            'prefill_strategy': 'golden_cross',
        })

        self.assertEqual(response.status_code, 200)
        mock_download.assert_not_called()
        self.assertEqual(response.context['initial_ticker'], 'AAPL')
        self.assertEqual(response.context['initial_start_date'], '2003-05-05')
        self.assertEqual(response.context['initial_autoload'], True)
        self.assertEqual(response.context['initial_analysis_mode'], 'single')
        self.assertEqual(response.context['initial_prior_mode'], 'universe')
        self.assertEqual(response.context['initial_prefill_strategy'], 'golden_cross')
        self.assertContains(response, 'data-initial-ticker="AAPL"')
        self.assertContains(response, 'data-initial-analysis-mode="single"')
        self.assertContains(response, 'data-initial-prior-mode="universe"')
        self.assertContains(response, 'data-initial-prefill-strategy="golden_cross"')

    def test_download_n_clean_data_re_normalizes_fresh_cached_payload(self):
        cache_key = _make_cache_key('AAPL', '2003-05-05', '2026-03-22', True)
        _cache_set(cache_key, self.sample_price_frame().to_json(orient='split'))

        with patch('my_app.utils._download_with_retry') as mock_download:
            cached_data = download_n_clean_data('AAPL', '2003-05-05', '2026-03-22', compute_sma=True)

        mock_download.assert_not_called()
        self.assertAlmostEqual(cached_data.iloc[0]['Date'], pd.Timestamp('2003-05-05').timestamp())
        self.assertIsNone(cached_data.iloc[0]['sma_50'])
        self.assertIsNone(cached_data.iloc[0]['sma_200'])

    @patch('my_app.views.download_n_clean_data')
    def test_fetch_stock_data_returns_candles_and_clamps_future_end_date(self, mock_download):
        today = timezone.localdate()
        future_end_date = today + timedelta(days=30)
        mock_download.return_value = self.sample_price_frame()

        response = self.client.get(reverse('fetch_stock_data'), {
            'ticker': 'aapl',
            'start_date': '2003-05-05',
            'end_date': future_end_date.isoformat(),
        })

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertEqual(len(payload['data']), 2)
        self.assertEqual(payload['data'][0]['Open'], 10.0)
        self.assertEqual(payload['data'][0]['Close'], 10.5)
        mock_download.assert_called_once_with(
            'AAPL',
            '2003-05-05',
            today.isoformat(),
            compute_sma=True,
        )

    @patch('my_app.views.download_n_clean_data')
    def test_fetch_stock_data_serializes_nan_indicator_values_as_null(self, mock_download):
        frame = self.sample_price_frame()
        frame['sma_50'] = np.nan
        frame['sma_200'] = np.nan
        mock_download.return_value = frame

        response = self.client.get(reverse('fetch_stock_data'), {
            'ticker': 'AAPL',
            'start_date': '2003-05-05',
            'end_date': '2026-03-22',
        })

        payload = response.json()
        raw_response = response.content.decode('utf-8')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertIsNone(payload['data'][0]['sma_50'])
        self.assertIsNone(payload['data'][0]['sma_200'])
        self.assertNotIn('NaN', raw_response)

    @patch('my_app.views.download_n_clean_data')
    def test_fetch_stock_data_returns_json_error_for_provider_failure(self, mock_download):
        mock_download.side_effect = PriceDataError(
            'Unable to reach Yahoo Finance right now. Check your internet or DNS connection and try again.'
        )

        response = self.client.get(reverse('fetch_stock_data'), {
            'ticker': 'AAPL',
            'start_date': '2003-05-05',
            'end_date': '2025-03-22',
        })

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(payload['valid'])
        self.assertIn('Unable to reach Yahoo Finance right now', payload['error'])

    @patch('my_app.views.get_weighted_golden_cross_snapshot')
    @patch('my_app.views.get_live_golden_cross_snapshot')
    @patch('my_app.views.download_n_clean_data')
    def test_fetch_group_data_serializes_chart_rows_without_nan_tokens(self, mock_download, mock_live_snapshot, mock_weighted_snapshot):
        frame = self.sample_price_frame()
        frame['sma_50'] = np.nan
        frame['sma_200'] = np.nan
        mock_download.return_value = frame
        mock_live_snapshot.return_value = {'composite_score': 82.5}
        mock_weighted_snapshot.return_value = {'quality_score': 74.1}

        group = Stock_Group.objects.create(name='Big Tech')
        stock = Stock.objects.create(name='Apple', symbol='AAPL', sector='Tech')
        group.stocks.add(stock)

        response = self.client.get(reverse('fetch_group_data'), {
            'ticker_group': 'Big Tech',
            'start_date': '2003-05-05',
            'end_date': '2026-03-22',
        })

        payload = response.json()
        raw_response = response.content.decode('utf-8')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertEqual(payload['data'][0]['symbol'], 'AAPL')
        self.assertIsNone(payload['data'][0]['chartData'][0]['sma_50'])
        self.assertIsNone(payload['data'][0]['chartData'][0]['sma_200'])
        self.assertEqual(payload['data'][0]['golden_cross_quality_score'], 74.1)
        self.assertEqual(payload['data'][0]['golden_cross_live_score'], 82.5)
        self.assertIn('golden_cross_math_url', payload['data'][0])
        self.assertIn('research_url', payload['data'][0])
        self.assertNotIn('NaN', raw_response)

    def test_backtest_shell_exposes_watchlist_source_context(self):
        response = self.client.get(reverse('backtest'), {
            'ticker': 'AAPL',
            'analysis_mode': 'single',
            'prior_mode': 'universe',
            'prefill_strategy': 'golden_cross',
            'source_list': 'Golden Cross 10Y Weighted Backtest',
            'source_rank': '2',
            'source_score': '84.25',
            'source_signal': 'golden_cross_weighted',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['initial_source_context']['source_rank'], '2')
        self.assertEqual(response.context['initial_source_context']['source_signal'], 'golden_cross_weighted')
        self.assertContains(response, 'Watchlist source context')
        self.assertContains(response, 'Golden Cross 10Y Weighted Backtest')

    def test_backtest_shell_labels_momentum_watchlist_source_context(self):
        response = self.client.get(reverse('backtest'), {
            'ticker': 'AAPL',
            'analysis_mode': 'single',
            'prior_mode': 'universe',
            'prefill_strategy': 'momentum_12m',
            'source_list': 'Momentum 60-Day Leaders',
            'source_rank': '1',
            'source_score': '18.34',
            'source_signal': 'momentum_60',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['initial_source_context']['source_signal'], 'momentum_60')
        self.assertEqual(response.context['initial_source_context']['source_signal_label'], 'Momentum 60-Day Leaders')
        self.assertContains(response, 'Momentum 60-Day Leaders')


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class DeploymentHealthTests(TestCase):
    def test_health_endpoint_returns_ok_payload(self):
        response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['service'], 'trading-pro')
        self.assertIn('timestamp', payload)


class BayesianMathTests(TestCase):
    def test_estimate_universe_prior_uses_smoothed_success_rate(self):
        frame_one = pd.DataFrame({'target_success': [1, 1, 0, 1, np.nan]})
        frame_two = pd.DataFrame({'target_success': [0, 1, 0, 0, 1]})

        prior = estimate_universe_prior([frame_one, frame_two], alpha=1.0)

        self.assertGreater(prior['probability'], 0)
        self.assertLess(prior['probability'], 1)
        self.assertEqual(prior['support']['total'], 9)

    def test_binary_likelihood_and_correlation_penalty_shrink_posterior_move(self):
        base_signal = [0, 1, 1, 1, 0, 1, 0, 1, 1, 0]
        base_target = [0, 1, 1, 0, 0, 1, 0, 1, 1, 0]
        signal = pd.Series(base_signal * 4, dtype=bool)
        target = pd.Series(base_target * 4, dtype=float)

        likelihood = estimate_binary_likelihood(signal, target, observed_event=True)
        self.assertGreater(likelihood['likelihood_ratio'], 1.0)

        weight = estimate_signal_weight(signal.astype(float), [signal.astype(float)])
        self.assertLess(weight, 1.0)

        prior = 0.55
        full_posterior, _ = apply_evidence(prior, likelihood['likelihood_ratio'], weight=1.0)
        shrunk_posterior, _ = apply_evidence(prior, likelihood['likelihood_ratio'], weight=weight)

        self.assertGreater(full_posterior, prior)
        self.assertGreater(shrunk_posterior, prior)
        self.assertLess(shrunk_posterior, full_posterior)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class WatchlistAndResearchTests(TestCase):
    @patch('my_app.views.get_golden_cross_watchlist')
    def test_watchlist_golden_cross_api_returns_live_payload(self, mock_watchlist):
        mock_watchlist.return_value = {
            'valid': True,
            'as_of': '2026-03-23 10:15',
            'refresh_seconds': 300,
            'results': [
                {
                    'symbol': 'AAPL',
                    'composite_score': 87.4,
                    'days_since_cross': 12,
                    'spread_pct': 4.1,
                    'price_above_sma200_pct': 6.2,
                    'volume_ratio': 1.31,
                    'as_of': '2026-03-23',
                    'research_url': '/research/AAPL/',
                },
                {
                    'symbol': 'MSFT',
                    'composite_score': 79.8,
                    'days_since_cross': 17,
                    'spread_pct': 3.7,
                    'price_above_sma200_pct': 5.4,
                    'volume_ratio': 1.18,
                    'as_of': '2026-03-23',
                    'research_url': '/research/MSFT/',
                },
            ],
        }

        response = self.client.get(reverse('watchlist_golden_cross_api'))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertEqual(payload['results'][0]['symbol'], 'AAPL')
        self.assertEqual(payload['results'][0]['research_url'], '/research/AAPL/')
        self.assertEqual(payload['refresh_seconds'], 300)

    @patch('my_app.views.get_golden_cross_weighted_watchlist')
    def test_watchlist_golden_cross_weighted_api_returns_weighted_payload(self, mock_watchlist):
        mock_watchlist.return_value = {
            'valid': True,
            'as_of': '2026-03-23 10:15',
            'refresh_seconds': 300,
            'results': [
                {
                    'symbol': 'AAPL',
                    'quality_score': 78.2,
                    'win_rate': 0.61,
                    'avg_trade_return': 0.084,
                    'total_return_pct': 1.44,
                    'max_drawdown': -0.22,
                    'trade_count': 11,
                    'live_composite_score': 82.5,
                    'consensus_label': 'Strong Now + Strong History',
                    'research_url': '/research/AAPL/?source_list=Golden%20Cross',
                    'math_url': '/theMath/?section=watchlist_signals&signal=golden_cross_weighted&ticker=AAPL#watchlist-signals',
                },
            ],
        }

        response = self.client.get(reverse('watchlist_golden_cross_weighted_api'))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertEqual(payload['results'][0]['symbol'], 'AAPL')
        self.assertEqual(payload['results'][0]['quality_score'], 78.2)
        self.assertEqual(payload['results'][0]['consensus_label'], 'Strong Now + Strong History')
        self.assertIn('math_url', payload['results'][0])

    @patch('my_app.services.watchlist_service._one_day_momentum')
    @patch('my_app.services.watchlist_service.download_n_clean_data')
    @patch('my_app.services.watchlist_service.get_watchlist_universe')
    def test_momentum_watchlist_research_urls_include_source_context(
        self,
        mock_universe,
        mock_download,
        mock_one_day_momentum,
    ):
        cache.clear()
        mock_universe.return_value = ['AAPL', 'MSFT']

        def _download_side_effect(symbol, start, end, compute_sma=False):
            frame = pd.DataFrame([{
                'Date': pd.Timestamp('2025-01-02').timestamp(),
                'Close': 100.0,
                'Volume': 1_000_000,
            }])
            frame.attrs['symbol'] = symbol
            return frame

        mock_download.side_effect = _download_side_effect

        def _momentum_side_effect(frame, lookback, ref_date):
            base = {'AAPL': 0.22, 'MSFT': 0.12}[frame.attrs['symbol']]
            if lookback == 120:
                base -= 0.03
            return base

        mock_one_day_momentum.side_effect = _momentum_side_effect

        payload = get_momentum_watchlist()
        first_60 = payload['results']['mom-60'][0]
        first_120 = payload['results']['mom-120'][0]

        self.assertIn('source_signal=momentum_60', first_60['research_url'])
        self.assertIn('source_list=Momentum+60-Day+Leaders', first_60['research_url'])
        self.assertIn('source_signal=momentum_120', first_120['research_url'])
        self.assertIn('source_list=Momentum+120-Day+Leaders', first_120['research_url'])

    def test_research_backtest_url_prefills_momentum_when_source_signal_is_momentum(self):
        url = build_research_backtest_url('AAPL', source_context={
            'source_list': 'Momentum 60-Day Leaders',
            'source_rank': '1',
            'source_score': '18.34',
            'source_signal': 'momentum_60',
        })

        params = parse_qs(urlparse(url).query)
        self.assertEqual(params.get('prefill_strategy'), ['momentum_12m'])
        self.assertEqual(params.get('source_signal'), ['momentum_60'])
        self.assertEqual(params.get('source_list'), ['Momentum 60-Day Leaders'])

    def test_research_backtest_url_defaults_to_golden_cross_without_source_signal(self):
        url = build_research_backtest_url('AAPL', source_context={
            'source_list': 'Watchlist',
            'source_rank': '1',
            'source_score': '82.11',
        })

        params = parse_qs(urlparse(url).query)
        self.assertEqual(params.get('prefill_strategy'), ['golden_cross'])

    @patch('my_app.views.build_research_payload')
    def test_research_page_renders_fundamentals_and_backtest_cta(self, mock_research_payload):
        mock_research_payload.return_value = {
            'ticker': 'AAPL',
            'company_name': 'Apple Inc.',
            'company_summary': 'Consumer electronics and platform company.',
            'market_snapshot_items': [{'label': 'Last Price', 'display': '$212.00'}],
            'fundamentals_items': [{'label': 'Forward P/E', 'display': '27.10'}],
            'growth_items': [{'label': 'Revenue Growth', 'display': '7.40%'}],
            'golden_cross': {
                'state_label': 'Active',
                'state_class': 'is-active',
                'composite_score': 84.25,
                'signal_breakdown': [{'label': 'Days Since Cross', 'display': '10'}],
                'component_cards': [{'label': 'Spread', 'display': '62.00%'}],
                'as_of': '2026-03-23',
                'fast_sma': '$205.00',
                'slow_sma': '$194.00',
                'price': '$212.00',
            },
            'backtest_url': '/backtest/?ticker=AAPL&analysis_mode=single&prior_mode=universe&prefill_strategy=golden_cross',
        }

        response = self.client.get(reverse('research', args=['AAPL']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Apple Inc.')
        self.assertContains(response, 'Forward P/E')
        self.assertContains(response, 'Run on Backtest')
        self.assertContains(response, 'prefill_strategy=golden_cross')

    @patch('my_app.views.build_watchlist_signal_math_context')
    def test_the_math_watchlist_signals_section_renders(self, mock_math_context):
        mock_math_context.return_value = {
            'selected_signal': 'golden_cross_weighted',
            'selected_ticker': 'AAPL',
            'composite': {
                'formula': {'formula': 'composite_formula', 'components': []},
                'inputs': [],
                'component_rows': [],
            },
            'weighted': {
                'formula': {'formula': 'weighted_formula', 'components': []},
                'metrics': [],
                'component_rows': [],
                'window': {'start_date': '2016-03-23', 'end_date': '2026-03-23'},
            },
            'comparison': {
                'live_score': 82.5,
                'weighted_score': 74.1,
                'consensus_label': 'Strong Now + Strong History',
                'interpretation': 'The setup is strong now and historically.',
            },
            'leaderboards': {
                'live': {'results': []},
                'weighted': {'results': []},
            },
        }

        response = self.client.get(reverse('theMath'), {
            'section': 'watchlist_signals',
            'signal': 'golden_cross_weighted',
            'ticker': 'AAPL',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Watchlist Signals')
        self.assertContains(response, 'Golden Cross Composite Score')
        self.assertContains(response, 'Golden Cross Weighted Backtest Rank')

    @patch('my_app.views.build_research_payload')
    def test_research_page_handles_provider_error_gracefully(self, mock_research_payload):
        mock_research_payload.side_effect = PriceDataError('Unable to load research data for AAPL right now.')

        response = self.client.get(reverse('research', args=['AAPL']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Unable to load research data for AAPL right now.')

    def test_indicators_page_redirects_to_encyclopedia_indicators_category(self):
        response = self.client.get(reverse('indicators'))
        destination = reverse('encyclopedia_category', kwargs={'category_slug': 'indicators'})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, destination)

        category_response = self.client.get(destination)
        self.assertEqual(category_response.status_code, 200)
        self.assertContains(category_response, 'Indicators')
        self.assertContains(category_response, 'Bollinger Bands')
        self.assertContains(category_response, 'Relative Strength Index')


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class PortfolioViewTests(TestCase):
    def test_portfolio_view_uses_default_threefund_allocation_for_chart_and_balance(self):
        response = self.client.get(reverse('portfolio'))

        self.assertEqual(response.status_code, 200)
        chart_data = response.context['chart_data']
        if isinstance(chart_data, str):
            chart_data = json.loads(chart_data)

        self.assertEqual(chart_data['labels'], ['VTI', 'VXUS', 'BND'])
        self.assertEqual(chart_data['series'], [20.0, 30.0, 50.0])
        self.assertEqual(response.context['portfolio_top_sleeve']['ticker'], 'BND')
        self.assertEqual(response.context['portfolio_top_sleeve']['weight_display'], '50.00%')
        self.assertContains(response, '$20,000.00')

    def test_portfolio_view_uses_app_settings_limits_and_balance(self):
        app_settings = AppSettings.get_solo()
        app_settings.portfolio_builder_limit = 7
        app_settings.portfolio_ticker_limit = 12
        app_settings.portfolio_notional_balance = 35000
        app_settings.save()

        response = self.client.get(reverse('portfolio'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['portfolio_builder_limit'], 7)
        self.assertEqual(response.context['portfolio_ticker_limit'], 12)
        self.assertEqual(response.context['portfolio_balance_total'], 35000)
        self.assertContains(response, 'data-portfolio-limit="7"')
        self.assertContains(response, '$35,000.00')


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class AppSettingsViewTests(TestCase):
    def test_settings_page_saves_portfolio_and_backtest_defaults(self):
        response = self.client.post(reverse('settings'), data={
            'portfolio_builder_limit': 6,
            'portfolio_ticker_limit': 8,
            'portfolio_notional_balance': 45000,
            'backtest_default_start_date': '2001-01-01',
            'backtest_default_analysis_mode': 'multi',
            'backtest_default_prior_mode': 'golden_cross',
            'backtest_default_benchmark': 'QQQ',
            'backtest_default_horizon_days': 84,
            'backtest_default_prefill_strategy': 'momentum_12m',
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/settings/?saved=1', response.url)

        app_settings = AppSettings.get_solo()
        self.assertEqual(app_settings.portfolio_builder_limit, 6)
        self.assertEqual(app_settings.portfolio_ticker_limit, 8)
        self.assertEqual(app_settings.portfolio_notional_balance, 45000)
        self.assertEqual(app_settings.backtest_default_analysis_mode, 'multi')
        self.assertEqual(app_settings.backtest_default_prior_mode, 'golden_cross')
        self.assertEqual(app_settings.backtest_default_benchmark, 'QQQ')
        self.assertEqual(app_settings.backtest_default_horizon_days, 84)
        self.assertEqual(app_settings.backtest_default_prefill_strategy, 'momentum_12m')

    def test_backtest_uses_saved_app_defaults_when_query_params_are_absent(self):
        app_settings = AppSettings.get_solo()
        app_settings.backtest_default_start_date = date(2004, 6, 22)
        app_settings.backtest_default_analysis_mode = 'multi'
        app_settings.backtest_default_prior_mode = 'golden_cross'
        app_settings.backtest_default_benchmark = 'QQQ'
        app_settings.backtest_default_horizon_days = 90
        app_settings.backtest_default_prefill_strategy = 'golden_cross'
        app_settings.save()

        response = self.client.get(reverse('backtest'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['initial_start_date'], '2004-06-22')
        self.assertEqual(response.context['initial_analysis_mode'], 'multi')
        self.assertEqual(response.context['initial_prior_mode'], 'golden_cross')
        self.assertEqual(response.context['initial_benchmark'], 'QQQ')
        self.assertEqual(response.context['initial_horizon_days'], 90)
        self.assertEqual(response.context['initial_prefill_strategy'], 'golden_cross')
        self.assertContains(response, 'data-initial-analysis-mode="multi"')
        self.assertContains(response, 'data-initial-prior-mode="golden_cross"')


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class BayesianBacktestApiTests(TestCase):
    def setUp(self):
        ensure_strategy_definitions()

    @staticmethod
    def feature_frame(phase: float = 0.0):
        dates = pd.date_range('2020-01-01', periods=320, freq='B')
        base = np.arange(len(dates))
        close = 120 + (base * 0.08) + (12 * np.sin((base / 9.0) + phase))
        future_ret = np.roll(close, -126) / close - 1
        target_success = np.where(base < len(dates) - 126, (future_ret > 0).astype(int), np.nan)
        return pd.DataFrame({
            'Date': dates.view('int64') // 10**9,
            'Date_dt': dates,
            'Open': close - 0.5,
            'High': close + 1.5,
            'Low': close - 1.5,
            'Close': close,
            'Volume': np.full(len(dates), 1_000_000),
            'target_success': target_success,
        })

    def single_payload(self):
        return {
            'ticker': 'AAPL',
            'start_date': '2020-01-01',
            'end_date': '2021-12-31',
            'analysis_mode': 'single',
            'prior_mode': 'universe',
            'benchmark': 'SPY',
            'horizon_days': 126,
            'strategy_chain': [
                {
                    'slug': 'golden_cross',
                    'params': {
                        'fast_sma': 5,
                        'slow_sma': 20,
                        'order_percentage': 100,
                        'starting_cash': 100000,
                    },
                },
            ],
        }

    def multi_payload(self):
        payload = self.single_payload()
        payload['analysis_mode'] = 'multi'
        payload['strategy_chain'] = [
            payload['strategy_chain'][0],
            {
                'slug': 'momentum_12m',
                'params': {
                    'lookback': 20,
                    'buy_threshold': 0.0,
                    'exit_threshold': -0.02,
                    'order_percentage': 100,
                    'starting_cash': 100000,
                },
            },
        ]
        return payload

    @patch('my_app.services.backtest_service.load_training_frames')
    @patch('my_app.services.backtest_service.load_feature_frame')
    def test_api_run_backtest_single_strategy_persists_run(self, mock_feature_frame, mock_training_frames):
        mock_feature_frame.return_value = self.feature_frame()
        mock_training_frames.return_value = (
            [self.feature_frame(phase=0.0), self.feature_frame(phase=1.2)],
            ['SPY', 'AAPL'],
            {},
        )

        response = self.client.post(
            reverse('api_run_backtest'),
            data=json.dumps(self.single_payload()),
            content_type='application/json',
        )

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertEqual(payload['analysis_mode'], 'single')
        self.assertEqual(len(payload['strategies']), 1)
        self.assertEqual(BacktestRun.objects.count(), 1)
        self.assertEqual(StrategyRun.objects.count(), 1)
        self.assertEqual(EvidenceSnapshot.objects.count(), 1)
        self.assertGreaterEqual(TradeLog.objects.count(), 0)
        self.assertEqual(StrategyRun.objects.first().sequence_index, 1)
        self.assertIn('math', payload)
        self.assertIn('prior', payload['math'])
        self.assertEqual(len(payload['math']['steps']), 1)
        self.assertIn('signal_math', payload['math']['steps'][0])
        self.assertIn('likelihood_ratio', payload['math']['steps'][0])

    @patch('my_app.services.backtest_service.load_training_frames')
    @patch('my_app.services.backtest_service.load_feature_frame')
    def test_api_run_backtest_multi_strategy_orders_chain(self, mock_feature_frame, mock_training_frames):
        mock_feature_frame.return_value = self.feature_frame()
        mock_training_frames.return_value = (
            [self.feature_frame(phase=0.0), self.feature_frame(phase=1.5), self.feature_frame(phase=2.3)],
            ['SPY', 'AAPL', 'MSFT'],
            {},
        )

        response = self.client.post(
            reverse('api_run_backtest'),
            data=json.dumps(self.multi_payload()),
            content_type='application/json',
        )

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertEqual(payload['analysis_mode'], 'multi')
        self.assertEqual([item['sequence_index'] for item in payload['strategies']], [1, 2])
        self.assertEqual(StrategyRun.objects.count(), 2)
        self.assertEqual(list(StrategyRun.objects.values_list('sequence_index', flat=True)), [1, 2])
        self.assertIn('workflow_note', payload['ui'])

    def test_api_run_backtest_rejects_multiple_strategies_in_single_mode(self):
        payload = self.multi_payload()
        payload['analysis_mode'] = 'single'

        response = self.client.post(
            reverse('api_run_backtest'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        body = response.json()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(body['valid'])
        self.assertIn('exactly one strategy', body['error'])

    @patch('my_app.services.backtest_service.load_training_frames')
    @patch('my_app.services.backtest_service.load_feature_frame')
    def test_api_backtest_detail_returns_persisted_run(self, mock_feature_frame, mock_training_frames):
        mock_feature_frame.return_value = self.feature_frame()
        mock_training_frames.return_value = (
            [self.feature_frame(phase=0.0), self.feature_frame(phase=0.8)],
            ['SPY', 'AAPL'],
            {},
        )

        run_response = self.client.post(
            reverse('api_run_backtest'),
            data=json.dumps(self.single_payload()),
            content_type='application/json',
        )
        run_payload = run_response.json()

        detail_response = self.client.get(reverse('api_backtest_detail', args=[run_payload['run_id']]))
        detail_payload = detail_response.json()

        self.assertEqual(detail_response.status_code, 200)
        self.assertTrue(detail_payload['valid'])
        self.assertEqual(detail_payload['run_id'], run_payload['run_id'])
        self.assertIn('equity_curve', detail_payload)
        self.assertEqual(detail_payload['ticker'], 'AAPL')
        self.assertIn('math', detail_payload)
        self.assertIn('final', detail_payload['math'])

    @patch('my_app.services.backtest_service.load_training_frames')
    @patch('my_app.services.backtest_service.load_feature_frame')
    def test_api_backtest_detail_includes_trade_log_fields_needed_for_chart_markers(self, mock_feature_frame, mock_training_frames):
        mock_feature_frame.return_value = self.feature_frame()
        mock_training_frames.return_value = (
            [self.feature_frame(phase=0.0), self.feature_frame(phase=0.8)],
            ['SPY', 'AAPL'],
            {},
        )

        run_response = self.client.post(
            reverse('api_run_backtest'),
            data=json.dumps(self.single_payload()),
            content_type='application/json',
        )
        run_payload = run_response.json()
        backtest_run = BacktestRun.objects.get(id=run_payload['run_id'])

        TradeLog.objects.create(
            backtest_run=backtest_run,
            strategy_slug='golden_cross',
            sequence_index=1,
            entry_date=date(2020, 3, 2),
            exit_date=date(2020, 5, 4),
            entry_price=100.0,
            exit_price=115.0,
            shares=25,
            pnl=375.0,
            return_pct=0.15,
            outcome='win',
        )

        detail_response = self.client.get(reverse('api_backtest_detail', args=[run_payload['run_id']]))
        detail_payload = detail_response.json()

        self.assertEqual(detail_response.status_code, 200)
        self.assertTrue(detail_payload['valid'])
        self.assertEqual(detail_payload['run_id'], run_payload['run_id'])

        marker_trade = next(
            trade for trade in detail_payload['trade_log']
            if trade['strategy_slug'] == 'golden_cross' and trade['entry_date'] == '2020-03-02'
        )

        self.assertIn('sequence_index', marker_trade)
        self.assertIn('entry_date', marker_trade)
        self.assertIn('exit_date', marker_trade)
        self.assertEqual(marker_trade['sequence_index'], 1)
        self.assertEqual(marker_trade['exit_date'], '2020-05-04')

    @patch('my_app.services.backtest_service.load_training_frames')
    @patch('my_app.services.backtest_service.load_feature_frame')
    def test_the_math_page_supports_overview_and_run_detail(self, mock_feature_frame, mock_training_frames):
        mock_feature_frame.return_value = self.feature_frame()
        mock_training_frames.return_value = (
            [self.feature_frame(phase=0.0), self.feature_frame(phase=0.8)],
            ['SPY', 'AAPL'],
            {},
        )

        overview_response = self.client.get(reverse('theMath'))
        self.assertEqual(overview_response.status_code, 200)
        self.assertContains(overview_response, 'Computation Layers')
        self.assertContains(overview_response, 'Bayesian Math')

        run_response = self.client.post(
            reverse('api_run_backtest'),
            data=json.dumps(self.single_payload()),
            content_type='application/json',
        )
        run_payload = run_response.json()

        detail_response = self.client.get(reverse('theMath'), {
            'run_id': run_payload['run_id'],
            'section': 'bayesian',
        })

        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Prior Derivation')
        self.assertContains(detail_response, 'Posterior Update')
        self.assertContains(detail_response, f'#{run_payload["run_id"]}')

    def test_api_strategy_definitions_returns_supported_v1_strategies(self):
        response = self.client.get(reverse('api_strategy_definitions'))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        returned_slugs = [item['slug'] for item in payload['strategies']]
        self.assertIn('golden_cross', returned_slugs)
        self.assertIn('momentum_12m', returned_slugs)
        self.assertIn('golden_cross_bollinger_squeeze', returned_slugs)
        self.assertIn('golden_cross_bollinger_breakout_confirm', returned_slugs)

    @patch('my_app.services.backtest_service.load_training_frames')
    @patch('my_app.services.backtest_service.load_feature_frame')
    def test_backtest_page_sets_csrf_cookie_for_js_run_requests(self, mock_feature_frame, mock_training_frames):
        mock_feature_frame.return_value = self.feature_frame()
        mock_training_frames.return_value = (
            [self.feature_frame(phase=0.0), self.feature_frame(phase=1.2)],
            ['SPY', 'AAPL'],
            {},
        )

        csrf_client = Client(enforce_csrf_checks=True)
        page_response = csrf_client.get(reverse('backtest'))

        self.assertEqual(page_response.status_code, 200)
        self.assertIn('csrftoken', csrf_client.cookies)

        response = csrf_client.post(
            reverse('api_run_backtest'),
            data=json.dumps(self.single_payload()),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_client.cookies['csrftoken'].value,
        )

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class ProScanPortfolioApiTests(TestCase):
    def setUp(self):
        self.portfolio = Portfolio.objects.create(
            name='Income Sleeve',
            ticker='SPY,TLT',
            allocation='60,40',
            is_default=True,
        )

    def sample_feature_frame(self):
        dates = pd.date_range('2020-01-01', periods=40, freq='B')
        close = np.linspace(100, 120, len(dates))
        return pd.DataFrame({
            'Date': dates.view('int64') // 10**9,
            'Date_dt': dates,
            'Open': close - 0.5,
            'High': close + 1.0,
            'Low': close - 1.0,
            'Close': close,
            'Volume': np.full(len(dates), 1_000_000),
        })

    def test_pro_scan_portfolio_options_returns_preset_and_saved_lists(self):
        response = self.client.get(reverse('api_pro_scan_portfolio_options'))
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertTrue(any(item['type'] == 'saved' and item['name'] == 'Income Sleeve' for item in payload['saved_portfolios']))
        self.assertTrue(any(item['type'] == 'preset' and item['key'] == 'threefund' for item in payload['preset_portfolios']))
        saved_default = next(item for item in payload['saved_portfolios'] if item['name'] == 'Income Sleeve')
        self.assertTrue(saved_default['is_default'])

    @patch('my_app.views.download_n_clean_data')
    def test_pro_scan_run_portfolio_returns_aggregated_portfolio_results(self, mock_download):
        mock_download.return_value = self.sample_feature_frame()

        response = self.client.post(
            reverse('api_pro_scan_run_portfolio'),
            data=json.dumps({
                'selection_type': 'saved',
                'selection_key': str(self.portfolio.id),
                'strategy_slug': 'golden_cross',
                'start_date': '2020-01-01',
                'end_date': '2020-03-31',
                'strategy_params': {
                    'fast_sma': 5,
                    'slow_sma': 20,
                    'order_percentage': 100,
                },
            }),
            content_type='application/json',
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertEqual(payload['portfolio']['name'], 'Income Sleeve')
        self.assertEqual(len(payload['results']), 1)
        self.assertEqual(payload['results'][0]['portfolio_name'], 'Income Sleeve')
        self.assertEqual(len(payload['results'][0]['holdings']), 2)
        self.assertIn('trade_count', payload['results'][0])

    def test_builtin_stock_group_route_returns_controlled_response_without_database_group(self):
        response = self.client.get(reverse('stock_list', args=['S&P-500']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ticker Group')

    def test_pro_scan_pages_set_csrf_cookie_for_scan_requests(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.get(reverse('pro_scan'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrftoken', csrf_client.cookies)

        group_response = csrf_client.get(reverse('stock_list', args=['Dow-Jones-30']))
        self.assertEqual(group_response.status_code, 200)
        self.assertIn('csrftoken', csrf_client.cookies)

    @patch('my_app.views.get_weighted_golden_cross_snapshot')
    @patch('my_app.views.get_live_golden_cross_snapshot')
    @patch('my_app.views.download_n_clean_data')
    def test_fetch_group_data_uses_builtin_group_fallback_without_database_group(
        self,
        mock_download,
        mock_live_snapshot,
        mock_weighted_snapshot,
    ):
        mock_download.return_value = self.sample_feature_frame()
        mock_live_snapshot.return_value = {'composite_score': 61.5}
        mock_weighted_snapshot.return_value = {'quality_score': 74.25}

        response = self.client.get(reverse('fetch_group_data'), {
            'ticker_group': 'Dow-Jones-30',
            'start_date': '2020-01-01',
            'end_date': '2020-03-31',
        })
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertGreater(len(payload['data']), 0)
        self.assertIn('name', payload['data'][0])
        self.assertIn('symbol', payload['data'][0])
        self.assertEqual(payload['data'][0]['golden_cross_live_score'], 61.5)
        self.assertEqual(payload['data'][0]['golden_cross_quality_score'], 74.25)

    @patch('my_app.views.get_weighted_golden_cross_snapshot')
    @patch('my_app.views.get_live_golden_cross_snapshot')
    @patch('my_app.views.download_n_clean_data')
    def test_pro_scan_run_group_returns_summary_rows_without_chart_payload(
        self,
        mock_download,
        mock_live_snapshot,
        mock_weighted_snapshot,
    ):
        mock_download.return_value = self.sample_feature_frame()
        mock_live_snapshot.return_value = {'composite_score': 55.0}
        mock_weighted_snapshot.return_value = {'quality_score': 81.25}

        group = Stock_Group.objects.create(name='Big Tech')
        stock = Stock.objects.create(name='Apple', symbol='AAPL', sector='Tech')
        group.stocks.add(stock)

        response = self.client.post(
            reverse('api_pro_scan_run_group'),
            data=json.dumps({
                'group_name': 'Big Tech',
                'strategy_slug': 'golden_cross',
                'start_date': '2020-01-01',
                'end_date': '2020-03-31',
                'strategy_params': {
                    'fast_sma': 5,
                    'slow_sma': 20,
                    'order_percentage': 100,
                    'starting_cash': 100000,
                },
            }),
            content_type='application/json',
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertEqual(payload['group']['name'], 'Big Tech')
        self.assertEqual(len(payload['results']), 1)
        self.assertEqual(payload['results'][0]['symbol'], 'AAPL')
        self.assertIn('trade_count', payload['results'][0])
        self.assertNotIn('chartData', payload['results'][0])
        self.assertEqual(payload['results'][0]['golden_cross_live_score'], 55.0)
        self.assertEqual(payload['results'][0]['golden_cross_quality_score'], 81.25)

    @patch('my_app.views.get_weighted_golden_cross_snapshot')
    @patch('my_app.views.get_live_golden_cross_snapshot')
    @patch('my_app.views.download_n_clean_data')
    def test_pro_scan_run_group_normalizes_live_frames_missing_date_dt(
        self,
        mock_download,
        mock_live_snapshot,
        mock_weighted_snapshot,
    ):
        frame = self.sample_feature_frame().drop(columns=['Date_dt']).copy()
        mock_download.return_value = frame
        mock_live_snapshot.return_value = {'composite_score': 55.0}
        mock_weighted_snapshot.return_value = {'quality_score': 81.25}

        group = Stock_Group.objects.create(name='Live Group')
        stock = Stock.objects.create(name='Apple', symbol='AAPL', sector='Tech')
        group.stocks.add(stock)

        response = self.client.post(
            reverse('api_pro_scan_run_group'),
            data=json.dumps({
                'group_name': 'Live Group',
                'strategy_slug': 'golden_cross',
                'start_date': '2020-01-01',
                'end_date': '2020-03-31',
                'strategy_params': {
                    'fast_sma': 5,
                    'slow_sma': 20,
                    'order_percentage': 100,
                    'starting_cash': 100000,
                },
            }),
            content_type='application/json',
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertEqual(payload['results'][0]['status'], 'ok')
        self.assertEqual(payload['results'][0]['symbol'], 'AAPL')

    @patch('my_app.views.get_weighted_golden_cross_snapshot')
    @patch('my_app.views.get_live_golden_cross_snapshot')
    @patch('my_app.views.download_n_clean_data')
    def test_pro_scan_run_group_accepts_csrf_secured_browser_flow(
        self,
        mock_download,
        mock_live_snapshot,
        mock_weighted_snapshot,
    ):
        mock_download.return_value = self.sample_feature_frame()
        mock_live_snapshot.return_value = {'composite_score': 42.0}
        mock_weighted_snapshot.return_value = {'quality_score': 73.0}

        group = Stock_Group.objects.create(name='Secure Group')
        stock = Stock.objects.create(name='Apple', symbol='AAPL', sector='Tech')
        group.stocks.add(stock)

        csrf_client = Client(enforce_csrf_checks=True)
        page_response = csrf_client.get(reverse('stock_list', args=['Secure Group']))
        self.assertEqual(page_response.status_code, 200)
        self.assertIn('csrftoken', csrf_client.cookies)

        response = csrf_client.post(
            reverse('api_pro_scan_run_group'),
            data=json.dumps({
                'group_name': 'Secure Group',
                'strategy_slug': 'golden_cross',
                'start_date': '2020-01-01',
                'end_date': '2020-03-31',
                'strategy_params': {
                    'fast_sma': 5,
                    'slow_sma': 20,
                    'order_percentage': 100,
                    'starting_cash': 100000,
                },
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_client.cookies['csrftoken'].value,
        )

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['valid'])
        self.assertEqual(payload['results'][0]['symbol'], 'AAPL')
