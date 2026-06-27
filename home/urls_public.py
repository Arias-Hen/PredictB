"""Rutas REST públicas (para el frontend React). Montadas en /api/ ."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views_public import (
    CsrfView, LoginView, LogoutView, MeView, RegisterView,
    PasswordResetRequestView, PasswordResetConfirmView,
    ValoracionViewSet, ViviendaViewSet, InformeViewSet,
    LocationsView, ContactoView, PrediccionPrecio
)

router = DefaultRouter()
router.register(r'valoraciones', ValoracionViewSet, basename='valoraciones')
router.register(r'viviendas', ViviendaViewSet, basename='viviendas')
router.register(r'informes', InformeViewSet, basename='informes')

urlpatterns = [
    path('auth/csrf/', CsrfView.as_view(), name='public-csrf'),
    path('auth/login/', LoginView.as_view(), name='public-login'),
    path('auth/logout/', LogoutView.as_view(), name='public-logout'),
    path('auth/me/', MeView.as_view(), name='public-me'),
    path('auth/register/', RegisterView.as_view(), name='public-register'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='public-password-reset'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='public-password-reset-confirm'),
    path('locations/', LocationsView.as_view(), name='public-locations'),
    path('contacto/', ContactoView.as_view(), name='public-contacto'),
    path('prediccion/', PrediccionPrecio.as_view(), name='public-prediccion'),
    path('', include(router.urls)),
]
