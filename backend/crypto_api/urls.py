# backend/crypto_api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('coins/', views.CryptoListAPIView.as_view(), name='coin-list'),
    path('coins/<int:pk>/', views.CryptoDetailAPIView.as_view(), name='coin-detail'),
    path('tokenomics-detailed/', views.TokenomicsDetailedView.as_view(), name='tokenomics-detailed'),
    path('ohlc/<str:symbol>/', views.OHLCDataView.as_view(), name='ohlc-data'),
    path('trigger-parsing/', views.trigger_parsing, name='trigger-parsing'),
    path('', views.api_root, name='api-root'),
]