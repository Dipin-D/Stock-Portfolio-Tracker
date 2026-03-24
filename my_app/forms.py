from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import AppSettings, Portfolio

class CustomLoginForm(AuthenticationForm):
    username = forms. CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio

        fields = [
            'name', 'drag_percentage', 'rebalance_frequency', 
            'total_return', 'rebalance_bands', 'ticker', 'allocation'
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'portfolio-input',
                'placeholder': 'Three Fund Portfolio',
            }),
            'drag_percentage': forms.NumberInput(attrs={
                'class': 'portfolio-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.20',
            }),
            'rebalance_frequency': forms.Select(attrs={'class': 'portfolio-select'}),
            'total_return': forms.CheckboxInput(attrs={'class': 'portfolio-checkbox'}),
            'rebalance_bands': forms.CheckboxInput(attrs={'class': 'portfolio-checkbox'}),
            'ticker': forms.TextInput(attrs={
                'class': 'portfolio-input',
                'placeholder': 'VTI, VXUS, BND',
            }),
            'allocation': forms.TextInput(attrs={
                'class': 'portfolio-input',
                'placeholder': '20,30,50',
            }),
        }


class AppSettingsForm(forms.ModelForm):
    class Meta:
        model = AppSettings
        fields = [
            'portfolio_builder_limit',
            'portfolio_ticker_limit',
            'portfolio_notional_balance',
            'backtest_default_start_date',
            'backtest_default_analysis_mode',
            'backtest_default_prior_mode',
            'backtest_default_benchmark',
            'backtest_default_horizon_days',
            'backtest_default_prefill_strategy',
        ]

        widgets = {
            'portfolio_builder_limit': forms.NumberInput(attrs={'class': 'settings-input', 'min': '1', 'max': '12'}),
            'portfolio_ticker_limit': forms.NumberInput(attrs={'class': 'settings-input', 'min': '1', 'max': '30'}),
            'portfolio_notional_balance': forms.NumberInput(attrs={'class': 'settings-input', 'min': '0', 'step': '100'}),
            'backtest_default_start_date': forms.DateInput(attrs={'class': 'settings-input', 'type': 'date'}),
            'backtest_default_analysis_mode': forms.Select(attrs={'class': 'settings-input'}),
            'backtest_default_prior_mode': forms.Select(attrs={'class': 'settings-input'}),
            'backtest_default_benchmark': forms.TextInput(attrs={'class': 'settings-input', 'maxlength': '10'}),
            'backtest_default_horizon_days': forms.NumberInput(attrs={'class': 'settings-input', 'min': '1'}),
            'backtest_default_prefill_strategy': forms.Select(attrs={'class': 'settings-input'}),
        }
