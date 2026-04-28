"""
URL configuration for SENTINEL project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', lambda request: HttpResponse('SENTINEL backend is running. Try /admin/ or /api/')), 
    path('favicon.ico', lambda request: HttpResponse(status=204)),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/assets/', include('assets.urls')),
    path('api/signals/', include('signals.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
