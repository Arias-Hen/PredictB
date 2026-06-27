"""Rutas REST para el panel de administración. Montadas en /api/admin/ ."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views_admin import (
    AdminLoginView, AdminLogoutView, AdminMeView, AdminStatsView, LocationsView,
    UsersViewSet, ValoracionViewSet, InformeViewSet, ViviendaViewSet, ImagenViviendaViewSet,
)

router = DefaultRouter()
router.register(r'users', UsersViewSet, basename='admin-users')
router.register(r'valoraciones', ValoracionViewSet, basename='admin-valoraciones')
router.register(r'informes', InformeViewSet, basename='admin-informes')
router.register(r'viviendas', ViviendaViewSet, basename='admin-viviendas')
router.register(r'imagenes', ImagenViviendaViewSet, basename='admin-imagenes')

urlpatterns = [
    path('auth/login/', AdminLoginView.as_view(), name='admin-login'),
    path('auth/logout/', AdminLogoutView.as_view(), name='admin-logout'),
    path('auth/me/', AdminMeView.as_view(), name='admin-me'),
    path('stats/', AdminStatsView.as_view(), name='admin-stats'),
    path('locations/', LocationsView.as_view(), name='admin-locations'),
    path('', include(router.urls)),
]
