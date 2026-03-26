"""
URL configuration for tradingmachine project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from my_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('home/', views.home, name='home'),
    path('', views.CustomLoginView.as_view(), name='home'),
    path('health/', views.health, name='health'),
    path('encyclopedia/', views.encyclopedia_home, name='encyclopedia_home'),
    path('encyclopedia/<slug:category_slug>/', views.encyclopedia_category, name='encyclopedia_category'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('indicators/', views.indicators, name='indicators'),
    path("api/watchlist/momentum/", views.watchlist_momentum_api, name="watchlist_momentum_api"),
    path("api/watchlist/golden-cross/", views.watchlist_golden_cross_api, name="watchlist_golden_cross_api"),
    path("api/watchlist/golden-cross-weighted/", views.watchlist_golden_cross_weighted_api, name="watchlist_golden_cross_weighted_api"),
    path('research/<str:ticker>/', views.research, name='research'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('portfolio/delete/<int:portfolio_id>/', views.delete_portfolio, name='delete_portfolio'),
    path('get-portfolio-form/<int:portfolio_id>/', views.get_portfolio_form, name='get_portfolio_form'),
    path('get-default-panel/', views.get_default_portfolio_panel, name='get_default_portfolio_panel'),
    path('get-empty-form/', views.get_empty_form, name='get_empty_form'),
    path('get-preset-form/<str:preset_name>/', views.get_preset_form, name='get_preset_form'),
    path('theMath/', views.theMath, name='theMath'),
    path('backtest/', views.backtest, name='backtest'),
    path('render_indicator_partial/<str:indicator>/', views.render_indicator_partial, name='render_indicator_partial'),
    path('pro_scan/', views.pro_scan, name='pro_scan'),
    path('stocks/<str:group_name>/', views.stock_list, name='stock_list'),
    path('fetch_stock_data/', views.fetch_stock_data, name='fetch_stock_data'),
    path('fetch_group_data/', views.fetch_group_data, name='fetch_group_data'),
    path('api/pro-scan/portfolio-options/', views.api_pro_scan_portfolio_options, name='api_pro_scan_portfolio_options'),
    path('api/pro-scan/run-group/', views.api_pro_scan_run_group, name='api_pro_scan_run_group'),
    path('api/pro-scan/run-portfolio/', views.api_pro_scan_run_portfolio, name='api_pro_scan_run_portfolio'),
    path('api/strategies/definitions/', views.api_strategy_definitions, name='api_strategy_definitions'),
    path('api/backtest/run/', views.api_run_backtest, name='api_run_backtest'),
    path('api/backtest/<int:run_id>/', views.api_backtest_detail, name='api_backtest_detail'),
    path('settings/', views.settings, name='settings'),
    path('help/', views.help, name='help'),
    path('backtest_momentum/', views.backtest_momentum, name='backtest_momentum'),
]
