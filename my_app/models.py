from datetime import date

from django.db import models
import yfinance as yf
from django.contrib.auth.models import User



class Stock_Group(models.Model):
    name = models.CharField(max_length=100)  # e.g., Dow30, S&P500, etc

class Stock(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    sector = models.CharField(max_length=10)

    # Many-to-many relationship with StockGroup
    groups = models.ManyToManyField(Stock_Group, related_name="stocks")

class Portfolio(models.Model):
    name = models.CharField(max_length=100)
    drag_percentage = models.FloatField(default=0)
    rebalance_frequency = models.CharField(max_length=10, choices=[
            ('Yearly', 'Yearly'),
            ('Quarterly', 'Quarterly'),
            ('Monthly', 'Monthly')
        ], default='Yearly')
    total_return = models.BooleanField(default=False)
    rebalance_bands = models.BooleanField(default=False)
    ticker = models.CharField(max_length=100)
    allocation = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_default:
            Portfolio.objects.exclude(id=self.id).update(is_default=False)
        super(Portfolio, self).save(*args, **kwargs)


class StrategyDefinition(models.Model):
    slug = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    category = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    default_params = models.JSONField(default=dict)

    class Meta:
        ordering = ['name']


class BacktestRun(models.Model):
    ANALYSIS_MODE_SINGLE = 'single'
    ANALYSIS_MODE_MULTI = 'multi'
    ANALYSIS_MODE_CHOICES = [
        (ANALYSIS_MODE_SINGLE, 'Single Strategy Analysis'),
        (ANALYSIS_MODE_MULTI, 'Multi-Strategy Analysis'),
    ]

    PRIOR_MODE_UNIVERSE = 'universe'
    PRIOR_MODE_GOLDEN_CROSS = 'golden_cross'
    PRIOR_MODE_CHOICES = [
        (PRIOR_MODE_UNIVERSE, 'Universe Prior'),
        (PRIOR_MODE_GOLDEN_CROSS, 'Golden Cross Prior'),
    ]

    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ticker = models.CharField(max_length=16)
    start_date = models.DateField()
    end_date = models.DateField()
    horizon_days = models.IntegerField(default=126)
    analysis_mode = models.CharField(max_length=16, choices=ANALYSIS_MODE_CHOICES, default=ANALYSIS_MODE_SINGLE)
    prior_mode = models.CharField(max_length=32, choices=PRIOR_MODE_CHOICES, default=PRIOR_MODE_UNIVERSE)
    prior_value = models.FloatField()
    posterior_value = models.FloatField(null=True, blank=True)
    benchmark = models.CharField(max_length=16, default='SPY')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_COMPLETED)
    request_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class StrategyRun(models.Model):
    backtest_run = models.ForeignKey(BacktestRun, related_name='strategy_runs', on_delete=models.CASCADE)
    strategy = models.ForeignKey(StrategyDefinition, on_delete=models.CASCADE)
    sequence_index = models.PositiveIntegerField(default=1)
    params = models.JSONField(default=dict)
    signal_active = models.BooleanField(default=False)
    used_as_prior = models.BooleanField(default=False)
    strength_score = models.FloatField(null=True, blank=True)
    likelihood_ratio = models.FloatField(null=True, blank=True)
    weighted_log_lr = models.FloatField(null=True, blank=True)
    posterior_after = models.FloatField(null=True, blank=True)
    metrics = models.JSONField(default=dict)
    evidence_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['sequence_index']
        constraints = [
            models.UniqueConstraint(fields=['backtest_run', 'sequence_index'], name='unique_backtest_sequence_index'),
        ]


class TradeLog(models.Model):
    backtest_run = models.ForeignKey(BacktestRun, related_name='trades', on_delete=models.CASCADE)
    strategy_slug = models.CharField(max_length=64)
    sequence_index = models.PositiveIntegerField(default=1)
    entry_date = models.DateField()
    exit_date = models.DateField(null=True, blank=True)
    entry_price = models.FloatField()
    exit_price = models.FloatField(null=True, blank=True)
    shares = models.FloatField(default=0)
    pnl = models.FloatField(null=True, blank=True)
    return_pct = models.FloatField(null=True, blank=True)
    outcome = models.CharField(max_length=16, blank=True)

    class Meta:
        ordering = ['entry_date', 'sequence_index']


class EvidenceSnapshot(models.Model):
    backtest_run = models.OneToOneField(BacktestRun, related_name='evidence_snapshot', on_delete=models.CASCADE)
    prior_probability = models.FloatField()
    posterior_probability = models.FloatField()
    evidence_json = models.JSONField(default=dict)
    explanation_json = models.JSONField(default=dict)


class AppSettings(models.Model):
    DEFAULT_BACKTEST_START_DATE = date(1993, 1, 1)

    ANALYSIS_MODE_CHOICES = [
        ('single', 'Single Strategy Analysis'),
        ('multi', 'Multi-Strategy Analysis'),
    ]
    PRIOR_MODE_CHOICES = [
        ('universe', 'Universe Prior'),
        ('golden_cross', 'Golden Cross Prior'),
    ]
    PREFILL_STRATEGY_CHOICES = [
        ('', 'No Prefill'),
        ('golden_cross', 'Golden Cross'),
        ('momentum_12m', 'Momentum 12M'),
    ]

    portfolio_builder_limit = models.PositiveIntegerField(default=5)
    portfolio_ticker_limit = models.PositiveIntegerField(default=10)
    portfolio_notional_balance = models.FloatField(default=20000)
    backtest_default_start_date = models.DateField(default=DEFAULT_BACKTEST_START_DATE)
    backtest_default_analysis_mode = models.CharField(
        max_length=16,
        choices=ANALYSIS_MODE_CHOICES,
        default='single',
    )
    backtest_default_prior_mode = models.CharField(
        max_length=32,
        choices=PRIOR_MODE_CHOICES,
        default='universe',
    )
    backtest_default_benchmark = models.CharField(max_length=16, default='SPY')
    backtest_default_horizon_days = models.PositiveIntegerField(default=126)
    backtest_default_prefill_strategy = models.CharField(
        max_length=64,
        choices=PREFILL_STRATEGY_CHOICES,
        blank=True,
        default='',
    )
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        return cls.objects.get_or_create(pk=1)[0]
