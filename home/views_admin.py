"""
API REST para el panel de administración (consumida desde React).

Autenticación: SessionAuthentication (cookie de Django) + BasicAuthentication para pruebas.
Permisos: IsAdminUser en todo (requiere is_staff=True). Excepción: AdminLoginView.

Rutas montadas en /api/admin/  (ver home/urls_admin.py).
"""
import io
import pandas as pd

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.http import HttpResponse

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Users, Valoracion, Informe, Vivienda, ImagenVivienda
from .serializers import (
    UsersSerializer, ValoracionSerializer, InformeSerializer,
    ViviendaSerializer, ImagenViviendaSerializer,
)


# ============================================================
# Auth
# ============================================================

class AdminLoginView(APIView):
    """POST {usuario, password} -> set session cookie. Requiere is_staff."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        usuario = request.data.get('usuario') or request.data.get('username')
        password = request.data.get('password')
        if not usuario or not password:
            return Response(
                {'error': 'usuario y password requeridos'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = authenticate(request, username=usuario, password=password)
        if user is None:
            return Response(
                {'error': 'Credenciales inválidas'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {'error': 'Cuenta desactivada'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not user.is_staff:
            return Response(
                {'error': 'Sin permisos de administración'},
                status=status.HTTP_403_FORBIDDEN,
            )
        login(request, user)
        return Response(_user_payload(user))


class AdminLogoutView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        logout(request)
        return Response({'success': True})


class AdminMeView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(_user_payload(request.user))


def _user_payload(user):
    return {
        'id': user.uniqueid,
        'usuario': user.usuario,
        'email': user.email,
        'nombre': user.nombre,
        'empresa': user.empresa,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'is_active': user.is_active,
    }


# ============================================================
# Users (gestión de usuarios desde admin)
# ============================================================

class UsersViewSet(viewsets.ModelViewSet):
    queryset = Users.objects.all().order_by('uniqueid')
    serializer_class = UsersSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['usuario', 'email', 'nombre', 'empresa']
    ordering_fields = ['uniqueid', 'usuario', 'date_joined', 'last_login']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if (empresa := params.get('empresa')):
            qs = qs.filter(empresa=empresa)
        if (estado := params.get('estado')) is not None:
            qs = qs.filter(estado=estado.lower() in ('true', '1', 'si'))
        if (is_active := params.get('is_active')) is not None:
            qs = qs.filter(is_active=is_active.lower() in ('true', '1'))
        if (is_staff := params.get('is_staff')) is not None:
            qs = qs.filter(is_staff=is_staff.lower() in ('true', '1'))
        return qs

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.is_superuser:
            return Response(
                {'error': 'No se puede eliminar un superusuario'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.pk == request.user.pk:
            return Response(
                {'error': 'No puedes eliminarte a ti mismo'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='set-password')
    def set_password(self, request, pk=None):
        """Restablece la contraseña de un usuario (p.ej. si la olvidó).

        POST {password}. Valida la fortaleza con AUTH_PASSWORD_VALIDATORS, igual
        que el registro público.
        """
        user = self.get_object()
        password = request.data.get('password')
        if not password:
            return Response(
                {'error': 'password requerido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Valida la contraseña contra las reglas del proyecto (longitud, no común,
        # no similar a los datos del usuario, etc.).
        try:
            validate_password(password, user)
        except DjangoValidationError as exc:
            return Response(
                {'password': list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(password)
        user.save(update_fields=['password'])
        return Response({'success': True, 'usuario': user.usuario})

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return Response({'id': user.pk, 'is_active': user.is_active})


# ============================================================
# Valoraciones
# ============================================================

class ValoracionViewSet(viewsets.ModelViewSet):
    queryset = Valoracion.objects.select_related('iduser').order_by('-fecha_guardado')
    serializer_class = ValoracionSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['ciudad', 'distrito', 'barrio', 'calle']
    ordering_fields = ['idv', 'fecha_guardado', 'precio_esperado', 'metros_cuadrados']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        for field in ('ciudad', 'distrito', 'barrio', 'calle', 'modo', 'tipo_vivienda'):
            if (v := params.get(field)):
                qs = qs.filter(**{field: v})
        if (iduser := params.get('iduser')):
            qs = qs.filter(iduser=iduser)
        if (desde := params.get('fecha_desde')):
            qs = qs.filter(fecha_guardado__date__gte=desde)
        if (hasta := params.get('fecha_hasta')):
            qs = qs.filter(fecha_guardado__date__lte=hasta)
        return qs

    @action(detail=False, methods=['post'], url_path='export-excel')
    def export_excel(self, request):
        """POST {ids: [..]} -> xlsx. Si ids está vacío, exporta el queryset filtrado."""
        ids = request.data.get('ids') or []
        qs = self.get_queryset()
        if ids:
            qs = qs.filter(idv__in=ids)
        data = list(qs.values())
        if not data:
            return Response(
                {'error': 'No hay valoraciones para exportar'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        df = pd.DataFrame(data)
        # openpyxl no acepta datetimes con zona horaria ("Excel does not support
        # timezones in datetimes"): se quita la tz de cualquier columna fecha.
        for col in df.columns:
            if pd.api.types.is_datetime64tz_dtype(df[col]):
                df[col] = df[col].dt.tz_localize(None)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Valoraciones')
        resp = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = 'attachment; filename="valoraciones.xlsx"'
        return resp


# ============================================================
# Informes
# ============================================================

class InformeViewSet(viewsets.ModelViewSet):
    queryset = Informe.objects.all().select_related('usuario').order_by('-fecha_creacion')
    serializer_class = InformeSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', 'fecha_creacion']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if (uid := params.get('usuario')):
            qs = qs.filter(usuario_id=uid)
        if (q := params.get('q')):
            qs = qs.filter(
                Q(usuario__nombre__icontains=q) | Q(usuario__email__icontains=q)
            )
        return qs


# ============================================================
# Viviendas (entidad "Vivienda" — formulario de creación de anuncio)
# ============================================================

class ViviendaViewSet(viewsets.ModelViewSet):
    queryset = Vivienda.objects.all().prefetch_related('imagenes').order_by('-fecha_creacion')
    serializer_class = ViviendaSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', 'fecha_creacion', 'metros_cuadrados']


class ImagenViviendaViewSet(viewsets.ModelViewSet):
    queryset = ImagenVivienda.objects.all()
    serializer_class = ImagenViviendaSerializer
    permission_classes = [IsAdminUser]


# ============================================================
# Dashboard / stats
# ============================================================

class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({
            'usuarios': {
                'total': Users.objects.count(),
                'activos': Users.objects.filter(is_active=True).count(),
                'staff': Users.objects.filter(is_staff=True).count(),
            },
            'valoraciones': {
                'total': Valoracion.objects.count(),
                'por_modo': list(
                    Valoracion.objects.values('modo').annotate(total=Count('idv'))
                ),
                'por_ciudad': list(
                    Valoracion.objects.values('ciudad')
                    .annotate(total=Count('idv'))
                    .order_by('-total')[:10]
                ),
            },
            'informes': {
                'total': Informe.objects.count(),
            },
            'viviendas': {
                'total': Vivienda.objects.count(),
            },
        })


# ============================================================
# Cascading dropdowns (ciudad → distrito → barrio → calle) desde la BD
# Replica la lógica cacheada de ValoracionAdmin sin pasar por los CSV.
# ============================================================

class LocationsView(APIView):
    """
    GET /api/admin/locations/?level=ciudades
    GET /api/admin/locations/?level=distritos&ciudad=Madrid
    GET /api/admin/locations/?level=barrios&distrito=Centro
    GET /api/admin/locations/?level=calles&barrio=Sol
    """
    permission_classes = [IsAdminUser]

    LEVEL_FIELD = {
        'ciudades': 'ciudad',
        'distritos': 'distrito',
        'barrios': 'barrio',
        'calles': 'calle',
    }
    LEVEL_PARENT = {
        'distritos': 'ciudad',
        'barrios': 'distrito',
        'calles': 'barrio',
    }

    def get(self, request):
        level = request.query_params.get('level')
        if level not in self.LEVEL_FIELD:
            return Response(
                {'error': f"level inválido, usa uno de {list(self.LEVEL_FIELD)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        field = self.LEVEL_FIELD[level]
        qs = Valoracion.objects.all()
        parent = self.LEVEL_PARENT.get(level)
        if parent:
            parent_value = request.query_params.get(parent)
            if not parent_value:
                return Response(
                    {'error': f"se requiere query param '{parent}'"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(**{parent: parent_value})
        values = (
            qs.exclude(**{f'{field}__isnull': True})
            .exclude(**{field: ''})
            .values_list(field, flat=True)
            .distinct()
            .order_by(field)
        )
        return Response({'items': list(values)})
