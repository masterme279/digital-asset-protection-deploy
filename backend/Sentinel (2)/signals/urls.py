"""
URL patterns for signals app
"""
from django.urls import path
from .views import (
    ViolationsView,
    ForecastView,
    ThreatMapView,
    BlockchainProofsView,
    BlockchainModeView,
    BlockchainRegisterView,
    BlockchainVerifyView,
    BlockchainViolationView,
    DmcaNoticesView,
    AiHealthView,
    AiCasesView,
    AiAuditView,
    AiYouTubeMockIngestView,
    AiYouTubeRealIngestView,
    AiXRealIngestView,
    AiInstagramRealIngestView,
    AiRedditRealIngestView,
)

urlpatterns = [
    path('violations/', ViolationsView.as_view(), name='signals-violations'),
    path('forecast/', ForecastView.as_view(), name='signals-forecast'),
    path('threat-map/', ThreatMapView.as_view(), name='signals-threat-map'),
    path('blockchain/', BlockchainProofsView.as_view(), name='signals-blockchain'),
    path('blockchain/mode/', BlockchainModeView.as_view(), name='signals-blockchain-mode'),
    path('blockchain/register/', BlockchainRegisterView.as_view(), name='signals-blockchain-register'),
    path('blockchain/verify/', BlockchainVerifyView.as_view(), name='signals-blockchain-verify'),
    path('blockchain/violation/', BlockchainViolationView.as_view(), name='signals-blockchain-violation'),
    path('dmca/', DmcaNoticesView.as_view(), name='signals-dmca'),
    path('ai/health/', AiHealthView.as_view(), name='signals-ai-health'),
    path('ai/cases/', AiCasesView.as_view(), name='signals-ai-cases'),
    path('ai/audit/', AiAuditView.as_view(), name='signals-ai-audit'),
    path('ai/ingest/youtube/mock/', AiYouTubeMockIngestView.as_view(), name='signals-ai-youtube-mock-ingest'),
    path('ai/ingest/youtube/real/', AiYouTubeRealIngestView.as_view(), name='signals-ai-youtube-real-ingest'),
    path('ai/ingest/x/real/', AiXRealIngestView.as_view(), name='signals-ai-x-real-ingest'),
    path('ai/ingest/instagram/real/', AiInstagramRealIngestView.as_view(), name='signals-ai-instagram-real-ingest'),
    path('ai/ingest/reddit/real/', AiRedditRealIngestView.as_view(), name='signals-ai-reddit-real-ingest'),
]
