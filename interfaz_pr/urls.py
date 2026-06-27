"""
URL configuration for interfaz_pr.

Proyecto API-only: el frontend es React. Solo se exponen las dos APIs REST.
"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/', include('home.urls_public')),
    path('api/admin/', include('home.urls_admin')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
