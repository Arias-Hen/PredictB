"""
API REST pública (consumida por el frontend React).

Autenticación: SessionAuthentication (cookie). Para que la cookie viaje cross-origin
el front debe usar `credentials: 'include'` y mandar `X-CSRFToken`.

Rutas montadas en /api/  (ver home/urls_public.py).
"""
import io
import os

import pandas as pd

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files import File
from django.core.mail import EmailMessage
from django.db import IntegrityError
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie

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


@method_decorator(ensure_csrf_cookie, name='get')
class CsrfView(APIView):
    """Emite la cookie `csrftoken`. El front la llama una vez al arrancar para que
    axios pueda enviar el header `X-CSRFToken` en POST/PUT/PATCH/DELETE.

    Público y sin autenticación: así un usuario anónimo obtiene la cookie antes de
    registrarse/loguearse, no solo después de tener sesión."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'detail': 'CSRF cookie set'})


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

        # Valida la fortaleza de la contraseña con AUTH_PASSWORD_VALIDATORS.
        # Se pasa un usuario sin guardar para el chequeo de similitud (UserAttributeSimilarity).
        try:
            validate_password(password, Users(usuario=usuario, email=email, nombre=nombre))
        except DjangoValidationError as exc:
            return Response(
                {'password': list(exc.messages)},
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

        # Auto-login: deja la sesión iniciada tras registrar.
        # backend explícito porque hay varios AUTHENTICATION_BACKENDS configurados.
        login(request, user, backend='home.backends.CustomUserBackend')
        return Response(_user_payload(user), status=status.HTTP_201_CREATED)


class PasswordResetRequestView(APIView):
    """Solicita la recuperación de contraseña: envía un email con un enlace que
    apunta al frontend (`FRONTEND_URL/reset-password?uid=..&token=..`).

    Devuelve siempre 200 aunque el email no exista, para no revelar qué cuentas
    están registradas (evita enumeración de usuarios)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        usuario = (request.data.get('usuario') or '').strip()
        if not email and not usuario:
            return Response({'error': 'email o usuario requerido'},
                            status=status.HTTP_400_BAD_REQUEST)

        if email:
            user = Users.objects.filter(email__iexact=email, is_active=True).first()
        else:
            user = Users.objects.filter(usuario=usuario, is_active=True).first()

        if user and user.email:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?uid={uid}&token={token}"
            try:
                EmailMessage(
                    subject='Recuperación de contraseña - PredictBuild',
                    body=(
                        f'Hola {user.nombre or user.usuario},\n\n'
                        f'Recibimos una solicitud para restablecer tu contraseña.\n'
                        f'Abre este enlace para crear una nueva:\n\n{link}\n\n'
                        f'Si no fuiste tú, ignora este correo; tu contraseña seguirá igual.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                ).send()
            except Exception:
                # No se revela un fallo de envío al cliente (misma respuesta 200).
                pass

        return Response(
            {'detail': 'Si el correo está registrado, te enviaremos instrucciones.'}
        )


class PasswordResetConfirmView(APIView):
    """Confirma la recuperación: {uid, token, password} -> fija la nueva contraseña.

    `uid` y `token` vienen del enlace enviado por email."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password')
        if not all([uid, token, password]):
            return Response({'error': 'uid, token y password son requeridos'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            pk = urlsafe_base64_decode(uid).decode()
            user = Users.objects.get(pk=pk)
        except (TypeError, ValueError, OverflowError, Users.DoesNotExist):
            return Response({'error': 'Enlace inválido'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Enlace inválido o expirado'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(password, user)
        except DjangoValidationError as exc:
            return Response({'password': list(exc.messages)},
                            status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save(update_fields=['password'])
        return Response({'success': True})


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
        return (Valoracion.objects
                .select_related('iduser')
                .filter(iduser=self.request.user.uniqueid)
                .order_by('-fecha_guardado'))

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

    @action(detail=False, methods=['post'], url_path='export-excel')
    def export_excel(self, request):
        """POST {ids: [..]} -> xlsx con las filas seleccionadas en la tabla REGISTRO.

        Solo exporta valoraciones del propio usuario (get_queryset ya filtra por
        request.user), así que un id ajeno simplemente no aparece. Si `ids` viene
        vacío exporta todas las del usuario.
        """
        ids = request.data.get('ids') or []
        qs = self.get_queryset()
        if ids:
            qs = qs.filter(idv__in=ids)
        # Columnas legibles para el usuario (orden y nombres como en el registro).
        campos = [
            'fecha_guardado', 'modo', 'ciudad', 'distrito', 'barrio', 'calle',
            'planta', 'tipo_vivienda', 'estado_inmueble', 'metros_cuadrados',
            'num_habitaciones', 'num_banos', 'terraza', 'balcon', 'ascensor',
            'precio_minimo', 'precio_esperado', 'precio_maximo', 'precio_esperado_unico',
        ]
        data = list(qs.values(*campos))
        if not data:
            return Response(
                {'error': 'No hay valoraciones seleccionadas para exportar'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        df = pd.DataFrame(data, columns=campos)
        # fpdf/openpyxl no aceptan datetimes con tzinfo: se quita la zona horaria.
        if 'fecha_guardado' in df:
            df['fecha_guardado'] = pd.to_datetime(df['fecha_guardado']).dt.tz_localize(None)
        for col in ('terraza', 'balcon', 'ascensor'):
            df[col] = df[col].map({True: 'SI', False: 'NO'}).fillna(df[col])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Valoraciones')
        resp = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = 'attachment; filename="valoraciones_seleccionadas.xlsx"'
        return resp


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
        from .ai import generar_descripcion_vivienda

        # Valoración de origen (opcional). Se valida que pertenezca al usuario
        # logueado para que nadie pueda enlazar un informe a la valoración de otro.
        valoracion = None
        val_id = request.data.get('valoracion') or request.data.get('valoracion_id')
        if val_id:
            valoracion = Valoracion.objects.filter(
                idv=val_id, iduser=request.user.uniqueid,
            ).first()
            if valoracion is None:
                return Response(
                    {'error': 'valoracion no encontrada o no pertenece al usuario'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if valoracion is not None:
            # La valoración enlazada es la fuente de verdad: ignora lo que mande
            # el payload para que el PDF/informe no diverja de la valoración.
            m2 = valoracion.metros_cuadrados
            hab = valoracion.num_habitaciones
            banos = valoracion.num_banos
            ascensor = valoracion.ascensor
        else:
            m2 = request.data.get('metros_cuadrados')
            hab = request.data.get('habitaciones')
            banos = request.data.get('banos')
            ascensor_raw = request.data.get('ascensor')
            ascensor = str(ascensor_raw).lower() in ('true', '1', 'si', 'sí', 'yes')

        def _falta(v):
            return v is None or (isinstance(v, str) and v.strip() == '')

        if _falta(m2) or _falta(hab) or _falta(banos):
            return Response(
                {'error': 'metros_cuadrados, habitaciones y banos son requeridos'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Tipo de documento (informe | dossier); por defecto 'informe'.
        tipos_validos = {c[0] for c in Informe.TIPO_CHOICES}
        tipo = request.data.get('tipo', 'informe')
        if tipo not in tipos_validos:
            tipo = 'informe'

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
                    valoracion=valoracion,
                    tipo=tipo,
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
        return (Informe.objects
                .select_related('usuario', 'valoracion')
                .filter(usuario=self.request.user)
                .order_by('-fecha_creacion'))

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def generar(self, request):
        """Genera un informe/dossier a partir de una valoración del usuario.

        Campos (multipart): valoracion (id), tipo ('informe'|'dossier'),
        imagenes[] (archivos, opcionales). Crea el PDF desde plantilla y guarda
        un Informe asociado al usuario.
        """
        from .utils import generar_informe_pdf

        valoracion_id = request.data.get('valoracion') or request.data.get('valoracion_id')
        tipo = (request.data.get('tipo') or 'informe').lower()
        if tipo not in ('informe', 'dossier'):
            return Response({'error': "tipo debe ser 'informe' o 'dossier'"}, status=400)
        if not valoracion_id:
            return Response({'error': 'valoracion es requerida'}, status=400)

        try:
            valoracion = Valoracion.objects.get(idv=valoracion_id,
                                                iduser=request.user.uniqueid)
        except (Valoracion.DoesNotExist, ValueError):
            return Response({'error': 'Valoración no encontrada'}, status=404)

        import shutil
        import tempfile
        from django.core.files.base import ContentFile

        # fpdf necesita rutas de archivo para incrustar imágenes: las volcamos a un
        # directorio TEMPORAL que se borra al terminar (no deja basura en mediafiles).
        tmpdir = tempfile.mkdtemp(prefix='informe_imgs_')
        try:
            imagenes_paths = []
            for f in request.FILES.getlist('imagenes[]') + request.FILES.getlist('imagenes'):
                dest = os.path.join(tmpdir, os.path.basename(f.name))
                with open(dest, 'wb') as out:
                    for chunk in f.chunks():
                        out.write(chunk)
                imagenes_paths.append(dest)

            nombre, pdf_bytes = generar_informe_pdf(valoracion, tipo, imagenes_paths, request.user)
            # Una sola escritura: el FileField guarda el PDF en mediafiles/informes/.
            informe = Informe.objects.create(
                usuario=request.user,
                tipo=tipo,
                valoracion=valoracion,
                archivo_pdf=ContentFile(pdf_bytes, name=nombre),
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        from django.urls import reverse

        data = self.get_serializer(informe).data
        # `pdf_url`: enlace directo al archivo en /media/ (abrir en pestaña).
        data['pdf_url'] = data.get('archivo_pdf_url')
        # `download_url`: servido por la API (pasa por CORS), para que el front
        # pueda forzar la DESCARGA aunque esté en otro origen.
        data['download_url'] = request.build_absolute_uri(
            reverse('informes-download', args=[informe.id])
        )
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """Descarga el PDF del informe como adjunto.

        Se sirve desde la API (no desde /media/) para que el front, aunque esté
        en otro origen, pueda descargarlo y visualizarlo (CORS + Content-Disposition).
        Con ?inline=1 se muestra en el navegador en vez de forzar la descarga.
        """
        informe = self.get_object()
        if not informe.archivo_pdf:
            return Response({'error': 'El informe no tiene PDF'}, status=404)
        try:
            f = informe.archivo_pdf.open('rb')
        except (OSError, ValueError):
            return Response({'error': 'No se pudo leer el PDF'}, status=404)
        as_attachment = request.query_params.get('inline') not in ('1', 'true')
        filename = os.path.basename(informe.archivo_pdf.name)
        return FileResponse(
            f, as_attachment=as_attachment,
            filename=filename, content_type='application/pdf',
        )

    @action(detail=True, methods=['post'], url_path='enviar-email')
    def enviar_email(self, request, pk=None):
        """Envía el PDF del informe por email.

        Destinatario: `email` del body o, si no se indica, el del usuario logueado.
        """
        informe = self.get_object()
        if not informe.archivo_pdf:
            return Response({'error': 'El informe no tiene PDF'}, status=404)

        destinatario = (request.data.get('email') or request.user.email or '').strip()
        if not destinatario:
            return Response({'error': 'No hay email de destino'}, status=400)

        try:
            with informe.archivo_pdf.open('rb') as f:
                pdf_bytes = f.read()
        except (OSError, ValueError):
            return Response({'error': 'No se pudo leer el PDF'}, status=500)

        msg = EmailMessage(
            subject=f'{informe.get_tipo_display()} - PredictBuild',
            body=(
                f'Hola {request.user.nombre or request.user.usuario},\n\n'
                f'Adjuntamos el {informe.tipo} solicitado.\n\n'
                f'Un saludo,\nEquipo PredictBuild'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        msg.attach(os.path.basename(informe.archivo_pdf.name), pdf_bytes, 'application/pdf')
        try:
            msg.send()
        except Exception as exc:
            return Response({'error': f'Error enviando email: {exc}'}, status=500)
        return Response({'success': True, 'enviado_a': destinatario})


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