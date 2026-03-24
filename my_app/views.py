from datetime import date, datetime, timedelta
from typing import Optional
import json
import pandas as pd
import yfinance as yf

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.urls import reverse

from .forms import AppSettingsForm, CustomLoginForm, PortfolioForm
from .models import AppSettings, BacktestRun, Portfolio, Stock, Stock_Group
from .services.backtest_service import (
    list_strategy_definitions,
    run_bayesian_backtest,
    serialize_backtest_run,
)
from .services.research_service import build_research_payload
from .services.watchlist_service import (
    build_watchlist_signal_math_context,
    build_watchlist_math_url,
    get_golden_cross_watchlist,
    get_golden_cross_weighted_watchlist,
    get_golden_cross_consensus_label,
    get_live_golden_cross_snapshot,
    get_momentum_watchlist,
    get_weighted_golden_cross_snapshot,
)
from .utils import PriceDataError, download_n_clean_data, serialize_price_frame



class CustomLoginView(LoginView):
    template_name='home.html'
    authentication_form= CustomLoginForm
    
def home(request):
    return render(request, 'home.html')

def watchlist_view(request):
    return render(request, "watchlist.html")


def research(request, ticker: str):
    research_error = ''
    research_payload = None

    try:
        source_context = {
            'source_list': (request.GET.get('source_list') or '').strip(),
            'source_rank': (request.GET.get('source_rank') or '').strip(),
            'source_score': (request.GET.get('source_score') or '').strip(),
            'source_signal': (request.GET.get('source_signal') or '').strip(),
        }
        if not any(source_context.values()):
            source_context = None
        research_payload = build_research_payload(ticker, source_context=source_context)
    except PriceDataError as error:
        research_error = str(error)
    except Exception:
        research_error = f"Unable to load research data for {str(ticker or '').upper()} right now."

    return render(request, 'research.html', {
        'research_payload': research_payload,
        'research_error': research_error,
    })


def _split_csv_values(raw_value: str) -> list[str]:
    return [item.strip() for item in str(raw_value or '').split(',') if item.strip()]


def _get_app_settings() -> AppSettings:
    return AppSettings.get_solo()


def _build_portfolio_allocation_rows(portfolio: Portfolio | None, notional_balance: float) -> list[dict]:
    if portfolio is None:
        return []

    tickers = _split_csv_values(portfolio.ticker)
    raw_allocations = []
    for item in _split_csv_values(portfolio.allocation):
        try:
            raw_allocations.append(max(float(item), 0.0))
        except (TypeError, ValueError):
            raw_allocations.append(0.0)

    if not tickers:
        return []

    if len(raw_allocations) < len(tickers):
        raw_allocations.extend([0.0] * (len(tickers) - len(raw_allocations)))
    raw_allocations = raw_allocations[:len(tickers)]

    total_weight = sum(raw_allocations)
    if total_weight <= 0:
        normalized_weights = [100.0 / len(tickers)] * len(tickers)
    else:
        normalized_weights = [(weight / total_weight) * 100.0 for weight in raw_allocations]

    rows = []
    for ticker, weight_pct in zip(tickers, normalized_weights):
        notional_value = notional_balance * (weight_pct / 100.0)
        rows.append({
            'ticker': ticker,
            'weight_pct': round(weight_pct, 2),
            'weight_display': f"{weight_pct:.2f}%",
            'notional_value': round(notional_value, 2),
            'notional_display': f"${notional_value:,.2f}",
        })

    return rows


def _build_portfolio_context(default_portfolio: Portfolio | None, app_settings: AppSettings) -> dict:
    notional_balance = float(app_settings.portfolio_notional_balance or 0)
    allocation_rows = _build_portfolio_allocation_rows(default_portfolio, notional_balance)
    top_sleeve = max(allocation_rows, key=lambda row: row['weight_pct']) if allocation_rows else None
    chart_data = {
        "labels": [row['ticker'] for row in allocation_rows],
        "series": [row['weight_pct'] for row in allocation_rows],
    }

    return {
        'default_portfolio': default_portfolio,
        'app_settings': app_settings,
        'portfolio_balance_total': notional_balance,
        'portfolio_balance_display': f"${notional_balance:,.2f}",
        'portfolio_allocation_rows': allocation_rows,
        'portfolio_top_sleeve': top_sleeve,
        'portfolio_builder_limit': int(app_settings.portfolio_builder_limit or 5),
        'portfolio_ticker_limit': int(app_settings.portfolio_ticker_limit or 10),
        'portfolio_glidepath_leg_limit': 2,
        'chart_data': json.dumps(chart_data),
    }


def get_default_portfolio_panel(request):
    app_settings = _get_app_settings()
    default_portfolio = Portfolio.objects.filter(is_default=True).first()
    
    if not default_portfolio:
        default_portfolio = Portfolio(**PRESET_PORTFOLIOS['threefund'])

    return render(
        request,
        'partials/default_portfolio_panel.html',
        _build_portfolio_context(default_portfolio, app_settings),
    )

def portfolio(request):
    app_settings = _get_app_settings()
    if request.method == "POST":
        portfolio_id = request.POST.get('portfolio_id')
        form = PortfolioForm(request.POST, instance=Portfolio.objects.get(id=portfolio_id) if portfolio_id else None)

        if form.is_valid():
            new_portfolio = form.save(commit=False)

            # Explicitly handle checkbox state (checked or not)
            is_def = request.POST.get('is_default', False)
            if is_def:
                Portfolio.objects.update(is_default=False)
                new_portfolio.is_default = True
            else:
                new_portfolio.is_default = False
            
            new_portfolio.save()
            return redirect('portfolio')
        
    # On GET            
    form = PortfolioForm() 
    saved_forms = [(portfolio, PortfolioForm(instance=portfolio)) for portfolio in Portfolio.objects.all()]
    default_portfolio = Portfolio.objects.filter(is_default=True).first()

    # If no portfolio is marked default, fallback explicitly to Three Fund Portfolio preset
    if not default_portfolio:
        default_portfolio = Portfolio(**PRESET_PORTFOLIOS['threefund'])

    context = {
        'form': form,
        'saved_forms': saved_forms,
    }
    context.update(_build_portfolio_context(default_portfolio, app_settings))

    return render(request, 'portfolio.html', context)

def get_portfolio_form(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, id=portfolio_id)
    form = PortfolioForm(instance=portfolio)
    return render(request, 'partials/portfolio_form_partial.html', {'form': form, 'portfolio': portfolio})

# Dummy preset data templates
PRESET_PORTFOLIOS = {
    'permanent': {
        'name': 'Permanent Portfolio',
        'drag_percentage': 0.5,
        'rebalance_frequency': 'Yearly',
        'total_return': True,
        'rebalance_bands': False,
        'ticker': 'VTI,TLT,GLD,CASH',
        'allocation': '25,25,25,25',
    },
    'snp500': {
        'name': 'S&P 500',
        'drag_percentage': 0.15,
        'rebalance_frequency': 'Quarterly',
        'total_return': True,
        'rebalance_bands': True,
        'ticker': 'SPY',
        'allocation': '100',
    },
    'threefund': {
        'name': 'Three Fund Portfolio',
        'drag_percentage': 0.2,
        'rebalance_frequency': 'Yearly',
        'total_return': False,
        'rebalance_bands': True,
        'ticker': 'VTI, VXUS, BND',
        'allocation': '20,30,50',
    },
}

def get_preset_form(request, preset_name):
    data = PRESET_PORTFOLIOS.get(preset_name)
    if not data:
        return render(request, 'partials/portfolio_form_partial.html', {'form': None, 'portfolio': None})

    portfolio = Portfolio(**data)
    form = PortfolioForm(instance=portfolio)
    return render(request, 'partials/portfolio_form_partial.html', {'form': form, 'portfolio': portfolio})

def get_empty_form(request):
    empty_port = Portfolio()
    form = PortfolioForm(instance=empty_port)
    return render(request, "partials/portfolio_form_partial.html", {
        "form": form, 
        "portfolio": empty_port
    })


@require_POST
def delete_portfolio(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, id=portfolio_id)
    was_default = portfolio.is_default
    portfolio.delete()

    if was_default:
        replacement = Portfolio.objects.first()
        if replacement:
            replacement.is_default = True
            replacement.save()

    return JsonResponse({'deleted': True})


def theMath(request):
    run_id = request.GET.get('run_id')
    requested_section = (request.GET.get('section') or '').strip().lower()
    selected_section = requested_section or ('bayesian' if run_id else 'overview')
    math_run = None
    math_run_error = ''
    math_watchlist_context = None

    if run_id:
        try:
            parsed_run_id = int(run_id)
        except (TypeError, ValueError):
            math_run_error = 'The requested Bayesian run could not be found.'
        else:
            backtest_run = BacktestRun.objects.prefetch_related(
                'strategy_runs__strategy',
                'trades',
                'evidence_snapshot',
            ).filter(id=parsed_run_id).first()

            if backtest_run is None:
                math_run_error = 'The requested Bayesian run could not be found.'
            else:
                math_run = serialize_backtest_run(backtest_run)

    if selected_section == 'watchlist_signals':
        requested_signal = (request.GET.get('signal') or '').strip().lower()
        requested_ticker = (request.GET.get('ticker') or '').strip().upper()
        math_watchlist_context = build_watchlist_signal_math_context(requested_signal, requested_ticker)

    watchlist_signal_href = '?section=watchlist_signals#watchlist-signals'
    if math_watchlist_context:
        signal = math_watchlist_context.get('selected_signal')
        ticker = math_watchlist_context.get('selected_ticker')
        extra_query = []
        if signal:
            extra_query.append(f'signal={signal}')
        if ticker:
            extra_query.append(f'ticker={ticker}')
        if extra_query:
            watchlist_signal_href = f"?section=watchlist_signals&{'&'.join(extra_query)}#watchlist-signals"

    math_modules = [
        {
            'slug': 'bayesian',
            'title': 'Bayesian Math',
            'description': 'Live prior, LR, weighted log-LR, and posterior calculations for the selected run.',
            'available': bool(math_run),
            'href': (
                f"?run_id={math_run['run_id']}&section=bayesian#bayesian"
                if math_run else '#'
            ),
        },
        {
            'slug': 'watchlist_signals',
            'title': 'Watchlist Signals',
            'description': 'Live composite-score math, weighted 10Y Golden Cross rank math, and side-by-side signal comparison.',
            'available': True,
            'href': watchlist_signal_href,
        },
        {
            'slug': 'indicator-math',
            'title': 'Indicator Math',
            'description': 'Future derivations for indicator transforms and chart overlays.',
            'available': False,
            'href': '#',
        },
        {
            'slug': 'execution-math',
            'title': 'Execution Math',
            'description': 'Future fill models, slippage math, and execution assumptions.',
            'available': False,
            'href': '#',
        },
        {
            'slug': 'risk-positioning',
            'title': 'Risk & Position Sizing',
            'description': 'Future sizing equations, capital-at-risk logic, and stop structures.',
            'available': False,
            'href': '#',
        },
        {
            'slug': 'portfolio-construction',
            'title': 'Portfolio Construction',
            'description': 'Future allocation, exposure, and portfolio optimization math.',
            'available': False,
            'href': '#',
        },
        {
            'slug': 'scan-math',
            'title': 'Universe Scan Math',
            'description': 'Future ranking, lift scoring, and posterior scan methodology.',
            'available': False,
            'href': '#',
        },
    ]

    return render(request, 'theMath.html', {
        'math_run': math_run,
        'math_run_error': math_run_error,
        'math_watchlist_context': math_watchlist_context,
        'math_modules': math_modules,
        'selected_section': selected_section,
    })


BACKTEST_DEFAULT_START_DATE = date(1993, 1, 1)


def _coerce_autoload(value: str) -> bool:
    return str(value or '').strip().lower() in {'1', 'true', 'yes'}


def _parse_iso_date(raw_value: str) -> Optional[date]:
    if not raw_value:
        return None

    try:
        return datetime.strptime(raw_value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _build_backtest_shell_state(request):
    today = timezone.localdate()
    app_settings = _get_app_settings()
    ticker = (request.GET.get('ticker') or '').strip().upper()
    analysis_mode = (
        request.GET.get('analysis_mode')
        or app_settings.backtest_default_analysis_mode
        or BacktestRun.ANALYSIS_MODE_SINGLE
    ).strip().lower()
    if analysis_mode not in {BacktestRun.ANALYSIS_MODE_SINGLE, BacktestRun.ANALYSIS_MODE_MULTI}:
        analysis_mode = BacktestRun.ANALYSIS_MODE_SINGLE

    prior_mode = (
        request.GET.get('prior_mode')
        or app_settings.backtest_default_prior_mode
        or BacktestRun.PRIOR_MODE_UNIVERSE
    ).strip().lower()
    if prior_mode not in {BacktestRun.PRIOR_MODE_UNIVERSE, BacktestRun.PRIOR_MODE_GOLDEN_CROSS}:
        prior_mode = BacktestRun.PRIOR_MODE_UNIVERSE

    prefill_strategy = (
        request.GET.get('prefill_strategy')
        or app_settings.backtest_default_prefill_strategy
        or ''
    ).strip().lower()
    if prefill_strategy not in {'golden_cross', 'momentum_12m'}:
        prefill_strategy = ''

    default_start_date = app_settings.backtest_default_start_date or BACKTEST_DEFAULT_START_DATE

    start_date = _parse_iso_date(request.GET.get('start_date')) or default_start_date
    end_date = _parse_iso_date(request.GET.get('end_date'))

    normalized_start = min(start_date, today).isoformat() if start_date else default_start_date.isoformat()
    normalized_end = min(end_date, today).isoformat() if end_date else today.isoformat()
    autoload = _coerce_autoload(request.GET.get('autoload')) and bool(
        ticker and normalized_start and normalized_end
    )
    source_signal = (request.GET.get('source_signal') or '').strip().lower()
    source_context = {
        'source_list': (request.GET.get('source_list') or '').strip(),
        'source_rank': (request.GET.get('source_rank') or '').strip(),
        'source_score': (request.GET.get('source_score') or '').strip(),
        'source_signal': source_signal,
    }
    source_context['source_signal_label'] = {
        'golden_cross_composite': 'Golden Cross Live Composite',
        'golden_cross_weighted': 'Golden Cross 10Y Weighted Backtest',
    }.get(source_signal, source_context['source_signal'] or '')
    has_source_context = any(source_context.values())

    return {
        'initial_ticker': ticker,
        'initial_start_date': normalized_start,
        'initial_end_date': normalized_end,
        'initial_autoload': autoload,
        'initial_analysis_mode': analysis_mode,
        'initial_prior_mode': prior_mode,
        'initial_prefill_strategy': prefill_strategy,
        'initial_benchmark': (app_settings.backtest_default_benchmark or 'SPY').upper(),
        'initial_horizon_days': int(app_settings.backtest_default_horizon_days or 126),
        'initial_source_context': source_context if has_source_context else None,
    }


def _normalize_fetch_stock_request(request):
    today = timezone.localdate()
    ticker = (request.GET.get('ticker') or '').strip().upper()

    if not ticker:
        return None, 'Ticker is required.'

    raw_start_date = request.GET.get('start_date') or BACKTEST_DEFAULT_START_DATE.isoformat()
    raw_end_date = request.GET.get('end_date') or today.isoformat()

    start_date = _parse_iso_date(raw_start_date)
    if start_date is None:
        return None, 'Start date must use YYYY-MM-DD format.'

    end_date = _parse_iso_date(raw_end_date)
    if end_date is None:
        return None, 'End date must use YYYY-MM-DD format.'

    start_date = min(start_date, today)
    end_date = min(end_date, today)

    if start_date > end_date:
        return None, 'Start date must be on or before end date.'

    return {
        'ticker': ticker,
        'download_symbol': ticker.replace('.', '-'),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }, None


@ensure_csrf_cookie
def backtest(request):
    return render(request, 'backtest.html', _build_backtest_shell_state(request))

def render_indicator_partial(request, indicator):
    if indicator == 'sma':
        return render(request, 'partials/indicators/indicator_modal_ma.html')   
    elif indicator == 'ema':
        return render(request, 'partials/indicators/indicator_modal_ma.html')  
    elif indicator == 'bbands':
        pass
    elif indicator == 'rsi':        
        pass
    elif indicator == 'macd':
        pass
    elif indicator == 'adx':
        pass
    elif indicator == 'stoch':
        pass
    elif indicator == 'ichimoku':
        pass
    
def fetch_stock_data(request):
    normalized_request, error_message = _normalize_fetch_stock_request(request)
    if error_message:
        return JsonResponse({'valid': False, 'error': error_message}, status=200)

    try:
        clean_data = download_n_clean_data(
            normalized_request['download_symbol'],
            normalized_request['start_date'],
            normalized_request['end_date'],
            compute_sma=True,
        )

        if clean_data.empty:
            return JsonResponse({
                'valid': False,
                'error': f"No price data returned for {normalized_request['ticker']} in that date range."
            }, status=200)

        Stock.objects.get_or_create(symbol=normalized_request['ticker'])
        response_data = {'valid': True, 'data': serialize_price_frame(clean_data, compute_sma=True)}
        return JsonResponse(response_data)
    except PriceDataError as error:
        return JsonResponse({
            'valid': False,
            'error': str(error)
        }, status=200)
    except Exception:
        return JsonResponse({
            'valid': False,
            'error': 'Unexpected error while loading price data.'
        }, status=200)
    


@require_GET
def fetch_group_data(request):
    ticker_group = request.GET.get('ticker_group')
    start_date = request.GET.get('start_date', '1993-01-01')
    end_date = request.GET.get('end_date', '2020-02-16')

    result = []

    try:
        if not ticker_group:
            return JsonResponse({'valid': False, 'error': 'No ticker_group provided'})

        group = Stock_Group.objects.get(name=ticker_group)
        print("Found group:", group.name)

        # Exclude the problematic ticker:
        tickers = group.stocks.exclude(symbol='MRPW').values_list('symbol', flat=True)
        print("Tickers in group:", tickers)

        for symbol in tickers:
            yf_symbol = symbol.replace('.', '-')
            live_snapshot = get_live_golden_cross_snapshot(symbol, require_active=False) or {}
            weighted_snapshot = get_weighted_golden_cross_snapshot(symbol) or {}
            quality_score = float(weighted_snapshot.get('quality_score', 0.0))
            live_score = float(live_snapshot.get('composite_score', 0.0))
            consensus_label = get_golden_cross_consensus_label(live_score, quality_score)
            research_url = reverse('research', args=[symbol])
            math_url = build_watchlist_math_url('golden_cross_weighted', symbol)
            if not Stock.objects.filter(symbol=symbol).exists():
                print(f"Symbol {symbol} not found in DB")
                result.append({
                    'symbol': symbol,
                    'chartData': [],
                    'golden_cross_quality_score': quality_score,
                    'golden_cross_live_score': live_score,
                    'golden_cross_consensus_label': consensus_label,
                    'golden_cross_math_url': math_url,
                    'research_url': research_url,
                })
                continue

            try:
                clean_data = download_n_clean_data(yf_symbol, start_date, end_date, compute_sma=True)
                result.append({
                    'symbol': symbol,
                    'chartData': serialize_price_frame(clean_data, compute_sma=True),
                    'golden_cross_quality_score': quality_score,
                    'golden_cross_live_score': live_score,
                    'golden_cross_consensus_label': consensus_label,
                    'golden_cross_math_url': math_url,
                    'research_url': research_url,
                })
            except Exception as e:
                print(f"Error processing {symbol}: {str(e)}")
                result.append({
                    'symbol': symbol,
                    'chartData': [],
                    'golden_cross_quality_score': quality_score,
                    'golden_cross_live_score': live_score,
                    'golden_cross_consensus_label': consensus_label,
                    'golden_cross_math_url': math_url,
                    'research_url': research_url,
                })

        return JsonResponse({'valid': True, 'data': result})
    
    except Stock_Group.DoesNotExist:
            print("Group not found:", ticker_group)
            return JsonResponse({'valid': False, 'error': f'Group {ticker_group} not found'}, status=200)
    except Exception as e:
            print("Error in fetch_group_data:", str(e))
            return JsonResponse({'valid': False, 'error': str(e)}, status=200)


@require_GET
def api_strategy_definitions(request):
    return JsonResponse({
        'valid': True,
        'strategies': list_strategy_definitions(),
    })


@require_POST
def api_run_backtest(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({
            'valid': False,
            'error': 'Request body must be valid JSON.'
        }, status=400)

    try:
        result = run_bayesian_backtest(payload, user=request.user)
        return JsonResponse({
            'valid': True,
            **result,
        })
    except PriceDataError as error:
        return JsonResponse({
            'valid': False,
            'error': str(error),
        }, status=200)
    except ValueError as error:
        return JsonResponse({
            'valid': False,
            'error': str(error),
        }, status=400)
    except Exception:
        return JsonResponse({
            'valid': False,
            'error': 'Unexpected error while running Bayesian backtest.'
        }, status=500)


@require_GET
def api_backtest_detail(request, run_id: int):
    backtest_run = get_object_or_404(BacktestRun.objects.prefetch_related(
        'strategy_runs__strategy',
        'trades',
        'evidence_snapshot',
    ), id=run_id)

    return JsonResponse({
        'valid': True,
        **serialize_backtest_run(backtest_run),
    })


def settings(request):
    app_settings = _get_app_settings()

    if request.method == 'POST':
        form = AppSettingsForm(request.POST, instance=app_settings)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('settings')}?saved=1")
    else:
        form = AppSettingsForm(instance=app_settings)

    return render(request, 'settings.html', {
        'form': form,
        'app_settings': app_settings,
        'settings_saved': request.GET.get('saved') == '1',
    })

def about_us(request):
    return render(request, 'about_us.html')

def help(request):
    return render(request, 'help.html')

def contact_us(request):
    return render(request, 'contact_us.html')

def pro_scan(request):
    return render(request, 'pro_scan.html')

def stock_list(request, group_name):
    group = Stock_Group.objects.get(name=group_name)
    stocks = group.stocks.all()
    return render(request, 'pro_scan.html', {'stocks': stocks})

@require_GET
def backtest_momentum(request):
    # /backtest_momentum/?ticker=SPY&start=2015-01-01&end=2025-08-01&lookback=60
    ticker = (request.GET.get('ticker') or '').upper()
    start = request.GET.get('start')
    end = request.GET.get('end')
    lookback = int(request.GET.get('lookback', 60))
    if not (ticker and start and end):
        return JsonResponse({'valid': False, 'error': 'Missing params'})
    df = yf.download(ticker, start=start, end=end)
    if df.empty:
        return JsonResponse({'valid': False, 'error': 'No data'})
    ohlc = [{'Date': idx.strftime('%Y-%m-%d'), 'Open': float(r.Open), 'High': float(r.High),
             'Low': float(r.Low), 'Close': float(r.Close)} for idx, r in df.iterrows()]
    return JsonResponse({'valid': True, 'ohlc': ohlc})

@require_GET
def watchlist_momentum_api(request):
    return JsonResponse(get_momentum_watchlist())


@require_GET
def watchlist_golden_cross_api(request):
    return JsonResponse(get_golden_cross_watchlist())


@require_GET
def watchlist_golden_cross_weighted_api(request):
    return JsonResponse(get_golden_cross_weighted_watchlist())

# WATCHLIST ########################################################
