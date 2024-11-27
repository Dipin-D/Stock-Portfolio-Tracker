from .import views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import login_view, logout_view, register_view,portfolio_view, front_view


urlpatterns = [
    path('', front_view, name='front'), 
    path('login/', login_view, name='login'), 
    path('logout/',logout_view, name='logout'),
    path('register/',register_view, name='register'),
    path('portfolio/', portfolio_view, name='portfolio'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
