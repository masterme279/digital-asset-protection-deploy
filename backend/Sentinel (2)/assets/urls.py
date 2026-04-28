"""
URL patterns for assets app
"""
from django.urls import path
from .views import AssetUploadView, AssetListView, AssetDetailView

urlpatterns = [
    path('upload/', AssetUploadView.as_view(), name='asset-upload'),
    path('', AssetListView.as_view(), name='asset-list'),
    path('<str:asset_id>/', AssetDetailView.as_view(), name='asset-detail'),
]
