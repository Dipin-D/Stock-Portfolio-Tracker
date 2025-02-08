from .import views
from django.urls import path
from django.conf import settings
from .views import login_view, logout_view, register_view,portfolio_view, front_view, backtest_view
from django.conf.urls.static import static


urlpatterns = [
    path('', front_view, name='front'), 
    path('login/', login_view, name='login'), 
    path('logout/',logout_view, name='logout'),
    path('register/',register_view, name='register'),
    path('portfolio/', portfolio_view, name='portfolio'),
    path('backtest/', backtest_view, name='backtest'),
    path('fetch_stock_data/', views.fetch_stock_data, name='fetch_stock_data'),
]
