import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_app', '0005_strategydefinition_backtestrun_evidencesnapshot_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('portfolio_builder_limit', models.PositiveIntegerField(default=5)),
                ('portfolio_ticker_limit', models.PositiveIntegerField(default=10)),
                ('portfolio_notional_balance', models.FloatField(default=20000)),
                ('backtest_default_start_date', models.DateField(default=datetime.date(1993, 1, 1))),
                ('backtest_default_analysis_mode', models.CharField(choices=[('single', 'Single Strategy Analysis'), ('multi', 'Multi-Strategy Analysis')], default='single', max_length=16)),
                ('backtest_default_prior_mode', models.CharField(choices=[('universe', 'Universe Prior'), ('golden_cross', 'Golden Cross Prior')], default='universe', max_length=32)),
                ('backtest_default_benchmark', models.CharField(default='SPY', max_length=16)),
                ('backtest_default_horizon_days', models.PositiveIntegerField(default=126)),
                ('backtest_default_prefill_strategy', models.CharField(blank=True, choices=[('', 'No Prefill'), ('golden_cross', 'Golden Cross'), ('momentum_12m', 'Momentum 12M')], default='', max_length=64)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
