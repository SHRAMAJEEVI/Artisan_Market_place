"""
URL configuration for village_market project.
"""
from django.contrib import admin
from django.urls import path, include
from market import views as market_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('market.urls')),
    path('login/', market_views.login_view, name='login'),
    path('register/', market_views.register_view, name='register'),
    path('logout/', market_views.logout_view, name='logout'),
    path('', market_views.index, name='index'),
]

