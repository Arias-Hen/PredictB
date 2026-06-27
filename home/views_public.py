"""
API REST pública (consumida por el frontend React).

Autenticación: SessionAuthentication (cookie). Para que la cookie viaje cross-origin
el front debe usar `credentials: 'include'` y mandar `X-CSRFToken`.

Rutas montadas en /api/  (ver home/urls_public.py).
"""
import os

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.core.files import File
from django.core.mail import EmailMessage
from django.db import IntegrityError

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from . import locations
from .models import Users, Valoracion, Vivienda, ImagenVivienda, Informe, PredictionModel
from .serializers import PredictionInputSerializer, ValoracionSerializer, ViviendaSerializer, InformeSerializer
from .utils import generar_pdf


# ============================================================
# Auth
# ============================================================

def _user_payload(user):
    return {
        'id': user.uniqueid,
        'usuario': user.usuario,
        'email': user.email,
        'nombre': user.nombre,
        'empresa': user.empresa,
        'is_staff': user.is_staff,
    }


class LoginView(APIView):
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
        login(request, user)
        return Response(_user_payload(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'success': True})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_payload(request.user))


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        usuario = request.data.get('usuario')
        email = request.data.get('email')
        password = request.data.get('password')
        nombre = request.data.get('nombre') or usuario
        empresa = request.data.get('empresa') or 'Mi Empresa'

        if not all([usuario, email, password]):
            return Response(
                {'error': 'usuario, email y password son requeridos'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = Users.objects.create(
                usuario=usuario,
                email=email,
                nombre=nombre,
                empresa=empresa,
                password=make_password(password),
                estado=True,
            )
        except IntegrityError:
            return Response(
                {'error': 'Usuario o email ya registrados'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(_user_payload(user), status=status.HTTP_201_CREATED)


# ============================================================
# Valoraciones — el usuario solo ve y modifica las suyas
# ============================================================

class ValoracionViewSet(viewsets.ModelViewSet):
    """CRUD sobre las valoraciones del usuario logueado."""
    serializer_class = ValoracionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['ciudad', 'distrito', 'barrio', 'calle']
    ordering_fields = ['idv', 'fecha_guardado', 'precio_esperado']

    def get_queryset(self):
        return Valoracion.objects.filter(iduser=self.request.user.uniqueid).order_by('-fecha_guardado')

    def perform_create(self, serializer):        
        serializer.save(iduser_id=self.request.user.uniqueid)

    @action(detail=False, methods=['post'])
    def radar(self, request):
        """POST con los mismos datos que el formulario -> datos de radar normalizados."""
        required = ['ciudad', 'distrito', 'barrio', 'tipo_vivienda',
                    'm2', 'num_habitaciones', 'num_banos', 'precio_esperado',
                    'terraza', 'balcon', 'ascensor']
        data = request.data
        missing = [f for f in required if f not in data]
        if missing:
            return Response({'error': f'Faltan campos: {missing}'}, status=400)
        radar = PredictionModel.get_radar_data(
            ciudad=data['ciudad'],
            distrito=data['distrito'],
            barrio=data['barrio'],
            tipo_vivienda=int(data['tipo_vivienda']),
            user_data={
                'm2': data['m2'],
                'num_habitaciones': data['num_habitaciones'],
                'num_banos': data['num_banos'],
                'precio_medio': data['precio_esperado'],
                'terraza': data['terraza'],
                'balcon': data['balcon'],
                'ascensor': data['ascensor'],
            },
        )
        if 'error' in radar:
            return Response(radar, status=500)
        return Response(radar)


# ============================================================
# Locations (ciudades/distritos/barrios/calles) desde CSV cacheado
# ============================================================

class LocationsView(APIView):
    permission_classes = [AllowAny]

    LEVELS = ('ciudades', 'distritos', 'barrios', 'calles')

    def get(self, request):
        level = request.query_params.get('level')
        if level not in self.LEVELS:
            return Response(
                {'error': f"level inválido, usa uno de {list(self.LEVELS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if level == 'ciudades':
            items = locations.ciudades()
        elif level == 'distritos':
            ciudad = request.query_params.get('ciudad')
            if not ciudad:
                return Response({'error': "se requiere query param 'ciudad'"}, status=400)
            items = locations.distritos(ciudad)
        elif level == 'barrios':
            distrito = request.query_params.get('distrito')
            if not distrito:
                return Response({'error': "se requiere query param 'distrito'"}, status=400)
            items = locations.barrios(distrito)
        else:  # calles
            barrio = request.query_params.get('barrio')
            if not barrio:
                return Response({'error': "se requiere query param 'barrio'"}, status=400)
            items = locations.calles(barrio)
        return Response({'items': items})


# ============================================================
# Viviendas — crea anuncio + descripción IA + PDF
# ============================================================

class ViviendaViewSet(viewsets.ModelViewSet):
    queryset = Vivienda.objects.all().prefetch_related('imagenes')
    serializer_class = ViviendaSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        from .views import generar_descripcion_vivienda  # evita ciclo de imports
        m2 = request.data.get('metros_cuadrados')
        hab = request.data.get('habitaciones')
        banos = request.data.get('banos')
        ascensor_raw = request.data.get('ascensor')
        ascensor = str(ascensor_raw).lower() in ('true', '1', 'si', 'sí', 'yes')

        if not all([m2, hab, banos]):
            return Response(
                {'error': 'metros_cuadrados, habitaciones y banos son requeridos'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            descripcion = generar_descripcion_vivienda(m2, hab, banos, ascensor)
        except RuntimeError as exc:
            return Response({'error': str(exc)}, status=503)

        vivienda = Vivienda.objects.create(
            metros_cuadrados=m2,
            habitaciones=hab,
            banos=banos,
            ascensor=ascensor,
            descripcion=descripcion,
        )

        for f in request.FILES.getlist('imagenes[]') + request.FILES.getlist('imagenes'):
            ImagenVivienda.objects.create(vivienda=vivienda, imagen=f)

        imagenes_paths = [img.imagen.path for img in vivienda.imagenes.all()]
        ruta_pdf = generar_pdf(vivienda, imagenes_paths)

        # Guarda Informe asociado al usuario
        try:
            ruta_relativa = ruta_pdf.replace('/media/', '')
            ruta_completa = os.path.join(settings.MEDIA_ROOT, ruta_relativa)
            with open(ruta_completa, 'rb') as f:
                Informe.objects.create(
                    usuario=request.user,
                    archivo_pdf=File(f, name=os.path.basename(ruta_relativa)),
                )
        except OSError:
            pass

        return Response({
            'id': vivienda.id,
            'descripcion': descripcion,
            'pdf_url': ruta_pdf,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='enviar-email')
    def enviar_email(self, request, pk=None):
        """Envía el PDF de la vivienda por email al usuario logueado."""
        vivienda = self.get_object()
        imagenes_paths = [img.imagen.path for img in vivienda.imagenes.all()]
        ruta_pdf = generar_pdf(vivienda, imagenes_paths)
        ruta_relativa = ruta_pdf.replace('/media/', '')
        ruta_completa = os.path.join(settings.MEDIA_ROOT, ruta_relativa)

        try:
            with open(ruta_completa, 'rb') as f:
                pdf_bytes = f.read()
        except OSError:
            return Response({'error': 'No se pudo leer el PDF'}, status=500)

        msg = EmailMessage(
            subject='Informe de Vivienda',
            body=(
                f'Estimado/a {request.user.nombre},\n\n'
                f'Adjunto el informe PDF.\n\n{vivienda.descripcion}'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[request.user.email],
        )
        msg.attach('informe_vivienda.pdf', pdf_bytes, 'application/pdf')
        try:
            msg.send()
        except Exception as exc:
            return Response({'error': f'Error enviando email: {exc}'}, status=500)
        return Response({'success': True, 'enviado_a': request.user.email})


# ============================================================
# Informes — solo del usuario logueado
# ============================================================

class InformeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InformeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Informe.objects.filter(usuario=self.request.user).order_by('-fecha_creacion')


# ============================================================
# Contacto (formulario público)
# ============================================================

class ContactoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        d = request.data
        required = ['nombre_completo', 'correo_electronico', 'motivo_consulta']
        missing = [f for f in required if not d.get(f)]
        if missing:
            return Response({'error': f'Faltan campos: {missing}'}, status=400)
        if not d.get('terms'):
            return Response({'error': 'Debes aceptar los términos'}, status=400)
        cuerpo = (
            f"Nombre: {d.get('nombre_completo')}\n"
            f"Email: {d.get('correo_electronico')}\n"
            f"Teléfono: {d.get('telefono', '')}\n"
            f"Empresa: {d.get('nombre_empresa', '')}\n"
            f"Cargo: {d.get('cargo_rol', '')}\n"
            f"Motivo: {d.get('motivo_consulta')}\n"
        )
        try:
            msg = EmailMessage(
                subject='Solicitud de demostración gratuita',
                body=cuerpo,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['Contactoigniteconsultor@gmail.com'],
                reply_to=[d.get('correo_electronico')],
            )
            msg.send()
        except Exception as exc:
            return Response({'error': f'Error enviando email: {exc}'}, status=500)
        return Response({'success': True})
# ============================================================
# Prediccion precio
# ============================================================
class PrediccionPrecio(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = PredictionInputSerializer(data=request.data)
        if serializer.is_valid():
            try:
                prediction = PredictionModel.predict(serializer.validated_data)
                return Response(prediction, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)