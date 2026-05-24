from django.forms import model_to_dict
from django.shortcuts import render, redirect
from .models import Users
import csv
from django.urls import reverse_lazy
import json
import os
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .utils import load_data, save_data
from datetime import datetime
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from .forms import LoginForms, RegistrationForm
from django.contrib import messages
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from functools import wraps
from django.contrib.auth import get_user_model
from .models import Valoracion
from urllib.parse import unquote
from .models import PredictionModel
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Vivienda, ImagenVivienda
from .utils import generar_pdf
import requests
from openai import OpenAI
from .models import Informe
from django.core.files import File
from django.core.mail import EmailMessage
import logging
import os
import logging
import smtplib
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Vivienda, ImagenVivienda, Informe
from django.core.files import File
from .utils import generar_pdf
from fpdf import FPDF
logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'home.html')

def inicio(request):
    return render(request, 'inicio.html')

def cfunciona(request):
    return render(request, 'cfunciona.html')

def casos(request):
    return render(request, 'casos.html')

def terminos(request):
    return render(request, 'terminos.html')

@login_required
def valoraciones(request):
    options = []
    user = request.user
    user_id = user.uniqueid
    user_nombre = user.nombre
    email = user.email
    try:
        with open('distritos.csv', newline='', encoding='ISO-8859-1') as csvfile:
            reader = csv.DictReader(csvfile)
            cities = set()  
            for row in reader:
                if 'ciudad' in row:
                    cities.add(row['ciudad'])

            options = [{'id': ciudad, 'name': ciudad} for ciudad in cities]

        if options:
            options_json = json.dumps(options)
        else:
            options_json = '[]'

    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        options_json = '[]'

    return render(request, 'valoraciones.html', {'options_json': options_json, 'user_id': user_id, 'user_nombre': user_nombre, 'email':user.email})

@csrf_exempt
@login_required
def ventas(request):
    user = request.user
    user_id = user.uniqueid
    user_nombre = user.nombre
    email = user.email
    context = []  
    context_json = '{}' 
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            context = {
                'modo': data.get('modo', ''),
                'ciudad': data.get('ciudad', ''),
                'distrito': data.get('distrito', ''),
                'barrio': data.get('barrio', ''),
                'calle': data.get('calle', ''),
                'tipo_vivienda': data.get('tipo_vivienda', ''),
                'm2': data.get('m2', ''),
                'num_habitaciones': data.get('num_habitaciones', ''),
                'num_banos': data.get('num_banos', ''),
                'planta': data.get('planta', ''),
                'terraza': data.get('terraza', ''),
                'balcon': data.get('balcon', ''),
                'ascensor': data.get('ascensor', ''),
                'estado': data.get('estado', ''),
                'precio_minimo': data.get('precio_minimo', ''),
                'precio_esperado': data.get('precio_esperado', ''),
                'precio_maximo': data.get('precio_maximo', ''),
                'precio_esperado_unico': data.get('precio_esperado_unico', ''),
    
            }
            
            request.session['context_json'] = json.dumps(context)
            
            context_json = json.dumps(context)
        except json.JSONDecodeError:
            context['error'] = 'Datos JSON inválidos.'

    context_json = request.session.get('context_json', '{}')

    options = []
    try:
        with open('distritos.csv', newline='', encoding='ISO-8859-1') as csvfile:
            reader = csv.DictReader(csvfile)
            cities = set()  
            for row in reader:
                if 'ciudad' in row:
                    cities.add(row['ciudad'])

            options = [{'id': ciudad, 'name': ciudad} for ciudad in cities]

        if options:
            options_json = json.dumps(options)
        else:
            options_json = '[]'
    
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        options_json = '[]'
    valoraciones = []
    try:
        valoraciones_qs = Valoracion.objects.filter(iduser=user_id)
        for val in valoraciones_qs:
            valoraciones.append({
                'idv': val.idv,
                'modo': val.modo,
                'ciudad': val.ciudad,
                'distrito': val.distrito,
                'barrio': val.barrio,
                'calle': val.calle,
                'tipo_vivienda': val.tipo_vivienda,
                'm2': val.metros_cuadrados,
                'num_habitaciones': val.num_habitaciones,
                'num_banos': val.num_banos,
                'planta': val.planta,
                'terraza': val.terraza,
                'balcon': val.balcon,
                'ascensor': val.ascensor,
                'estado': val.estado_inmueble,
                'fecha_guardado': val.fecha_guardado.strftime('%d/%m/%Y'),
                'precio_minimo': val.precio_minimo,
                'precio_esperado': val.precio_esperado,
                'precio_maximo': val.precio_maximo,
                'precio_esperado_unico': val.precio_esperado_unico,
            })
    except FileNotFoundError:
        print("Archivo de valoraciones no encontrado.")
    return render(request, 'ventas.html', {'options_json': options_json, 'context_json': context_json, 'valoraciones':valoraciones, 'user_nombre': user_nombre, 'user_id': user_id, 'email':user.email})

@csrf_exempt
@login_required
def informes(request):
    user = request.user
    user_id = user.uniqueid
    user_nombre = user.nombre
    email = user.email
    context = []  
    context_json = '{}' 

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            context = {
                # mismos campos...
            }
            request.session['context_json'] = json.dumps(context)
            context_json = json.dumps(context)
        except json.JSONDecodeError:
            context['error'] = 'Datos JSON inválidos.'

    context_json = request.session.get('context_json', '{}')

    # cargar ciudades desde el CSV
    options = []
    try:
        with open('distritos.csv', newline='', encoding='ISO-8859-1') as csvfile:
            reader = csv.DictReader(csvfile)
            cities = set(row['ciudad'] for row in reader if 'ciudad' in row)
            options = [{'id': ciudad, 'name': ciudad} for ciudad in cities]
        options_json = json.dumps(options) if options else '[]'
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        options_json = '[]'

    valoraciones_qs = Valoracion.objects.filter(iduser=user_id)
    valoraciones = [{
        'modo': val.modo,
        'ciudad': val.ciudad,
        'distrito': val.distrito,
        'barrio': val.barrio,
        'calle': val.calle,
        'tipo_vivienda': val.tipo_vivienda,
        'm2': val.metros_cuadrados,
        'num_habitaciones': val.num_habitaciones,
        'num_banos': val.num_banos,
        'planta': val.planta,
        'terraza': val.terraza,
        'balcon': val.balcon,
        'ascensor': val.ascensor,
        'estado': val.estado_inmueble,
        'fecha_guardado': val.fecha_guardado.strftime('%d/%m/%Y'),
        'precio_minimo': val.precio_minimo,
        'precio_esperado': val.precio_esperado,
        'precio_maximo': val.precio_maximo,
        'precio_esperado_unico': val.precio_esperado_unico,
    } for val in valoraciones_qs]

    return render(request, 'informes.html', {
        'options_json': options_json,
        'context_json': context_json,
        'valoraciones': valoraciones,
        'user_id': user_id,
        'user_nombre': user.nombre,
        'email':user.email
    })
def generarinf(request):
    return render(request, 'generarinf.html')

def get_distritos(request, ciudad):
    ciudad = unquote(ciudad)
    print(f"City received: {ciudad}")
    distritos = []
    try:
        with open('distritos.csv', newline='', encoding='ISO-8859-1') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['ciudad'] == ciudad:
                    distritos.append({'id': row['distrito'], 'name': row['distrito']})

        return JsonResponse({'distritos': distritos})

    except Exception as e:
        print(f"Error al leer el archivo CSV para distritos: {e}")
        return JsonResponse({'distritos': []})
    
def get_barrios(request, distrito):
    distrito = unquote(distrito)
    barrios = []
    try:
        with open('distrito_barrio.csv', newline='', encoding='ISO-8859-1') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['distrito'] == distrito:
                    barrios.append({'id': row['barrio'], 'name': row['barrio']})

        return JsonResponse({'barrio': barrios})

    except Exception as e:
        print(f"Error al leer el archivo CSV para barrios: {e}")
        return JsonResponse({'barrio': []})
    
def get_calles(request, barrios):
    barrios = unquote(barrios)
    calle = []
    try:
        with open('tb_todo_precio_m2.csv', newline='', encoding='ISO-8859-1') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['barrio'] == barrios:
                    if not any(c['name'] == row['calle'] for c in calle):
                        calle.append({'id': row['calle'], 'name': row['calle']})

        return JsonResponse({'calle': calle})

    except Exception as e:
        print(f"Error al leer el archivo CSV para barrios: {e}")
        return JsonResponse({'calle': []})
    
def guardar_valoracion(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nueva_valoracion = Valoracion.objects.create(
                idv = data.get("idv"),
                iduser_id = data.get("iduser"),
                modo=data.get("modo"),
                ciudad=data.get("ciudad"),
                distrito=data.get("distrito"),
                barrio=data.get("barrio"),
                calle=data.get("calle"),
                tipo_vivienda=data.get("tipo_vivienda"),
                metros_cuadrados=data.get("m2"),
                num_habitaciones=data.get("num_habitaciones"),
                num_banos=data.get("num_banos"),
                planta=data.get("planta"),
                terraza=bool(data.get("terraza")), 
                balcon=bool(data.get("balcon")),   
                ascensor=bool(data.get("ascensor")), 
                estado_inmueble=data.get("estado"),
                precio_minimo=data.get("precio_minimo"),
                precio_esperado=data.get("precio_esperado"),
                precio_maximo=data.get("precio_maximo"),
                precio_esperado_unico=data.get("precio_esperado_unico")
            )

            return JsonResponse({
                "message": "Valoración guardada correctamente",
                "data": {
                    "idv" : nueva_valoracion.idv,
                    "iduser": nueva_valoracion.iduser_id,
                    "modo": nueva_valoracion.modo,
                    "ciudad": nueva_valoracion.ciudad,
                    "distrito": nueva_valoracion.distrito,
                    "barrio": nueva_valoracion.barrio,
                    "calle": nueva_valoracion.calle,
                    "tipo_vivienda": nueva_valoracion.tipo_vivienda,
                    "metros_cuadrados": nueva_valoracion.metros_cuadrados,
                    "num_habitaciones": nueva_valoracion.num_habitaciones,
                    "num_banos": nueva_valoracion.num_banos,
                    "planta": nueva_valoracion.planta,
                    "terraza": nueva_valoracion.terraza,
                    "balcon": nueva_valoracion.balcon,
                    "ascensor": nueva_valoracion.ascensor,
                    "estado_inmueble": nueva_valoracion.estado_inmueble,
                    "fecha_guardado": nueva_valoracion.fecha_guardado,
                }
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Datos inválidos"}, status=400)

    return JsonResponse({"error": "Método no permitido"}, status=405)

@csrf_exempt
def modificar_valoracion(request):
    if request.method == 'POST':
        try:
            print("Raw data:", request.body)  # Depuración
            data = json.loads(request.body)
            print("Parsed data:", data)  # Depuración
            
            idv = data.get('idv')
            if not idv:
                return JsonResponse({"error": "ID requerido", "received_data": data}, status=400)
            
            try:
                valoracion = Valoracion.objects.get(idv=idv)
            except Valoracion.DoesNotExist:
                return JsonResponse({"error": f"Valoración con ID {idv} no existe"}, status=404)
            
            # Campos a actualizar
            campos = ['modo', 'ciudad', 'distrito', 'barrio', 'calle', 
                     'tipo_vivienda', 'metros_cuadrados', 'num_habitaciones',
                     'num_banos', 'planta', 'estado_inmueble']
            
            for campo in campos:
                if campo in data:
                    setattr(valoracion, campo, data[campo])
            
            # Campos booleanos — acepta SI/NO, true/false, 1/0, bool
            def _to_bool(v):
                if isinstance(v, bool):
                    return v
                if v is None:
                    return False
                return str(v).strip().lower() in ('si', 'sí', 'true', '1', 'yes')

            if 'terraza' in data:
                valoracion.terraza = _to_bool(data.get('terraza'))
            if 'balcon' in data:
                valoracion.balcon = _to_bool(data.get('balcon'))
            if 'ascensor' in data:
                valoracion.ascensor = _to_bool(data.get('ascensor'))
            
            valoracion.save()
            
            return JsonResponse({"success": True, "id": valoracion.idv})

        except json.JSONDecodeError as e:
            return JsonResponse({"error": "JSON inválido", "detail": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "Método no permitido"}, status=405)

def user_login(request):
    form = LoginForms(request.POST or None)
    
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    # Para solicitudes AJAX
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        next_url = request.GET.get('next', '/home/valoraciones/')
                        return JsonResponse({
                            'success': True, 
                            'redirect_url': next_url
                        })
                    else:
                        next_url = request.GET.get('next', '/home/valoraciones/')
                        return redirect(next_url)
                else:
                    error_msg = 'Cuenta desactivada. Contacta al administrador.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False, 
                            'message': error_msg
                        })
                    else:
                        messages.error(request, error_msg)
            else:
                error_msg = 'Usuario o contraseña incorrectos.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False, 
                        'message': error_msg
                    })
                else:
                    messages.error(request, error_msg)
        else:
            error_msg = 'Por favor completa todos los campos correctamente.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'message': error_msg
                })
            else:
                messages.error(request, error_msg)
    
    return redirect('/home/')

def user_register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        print("POST data:", request.POST)

        if form.is_valid():
            cd = form.cleaned_data
            username = cd['usuario']
            email = cd['email']
            password = cd['password']

            if Users.objects.filter(usuario=username).exists():
                messages.error(request, 'El nombre de usuario ya está en uso. Por favor, elige otro.')
            elif Users.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe una cuenta registrada con este email.')
            else:
                try:
                    new_user = Users(
                        usuario=cd['usuario'],  # <--- aquí el cambio
                        email=email,
                        nombre=username,
                        empresa='Mi Empresa',
                        password=make_password(password),
                        estado=True
                    )
                    new_user.save()
                    messages.success(request, '¡Registro exitoso! Ahora puedes iniciar sesión.')
                    return redirect('/home/login/')
                except IntegrityError as e:
                    messages.error(request, 'Hubo un error al registrar el usuario. Intenta nuevamente.')
                    print("Error al guardar usuario:", e)
        else:
            messages.error(request, 'Formulario inválido. Revisa los campos.')
            print("Errores del formulario:", form.errors)
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


@csrf_exempt
def exportar_excel(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            seleccionados = body.get('seleccionados', [])

            if not seleccionados:
                return HttpResponse("No hay datos seleccionados", status=400)

            df = pd.DataFrame(seleccionados)

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="valoraciones_seleccionadas.xlsx"'

            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Datos Seleccionados')

            return response
        except Exception as e:
            print(f"Error al exportar Excel: {e}")
            return HttpResponse(f"Error interno: {e}", status=500)
    else:
        return HttpResponse("Método no permitido", status=405)

def contacto(request):
    if request.method == 'POST':
        nombre_completo = request.POST.get('nombre_completo')
        correo_electronico = request.POST.get('correo_electronico')
        telefono = request.POST.get('telefono')
        nombre_empresa = request.POST.get('nombre_empresa')
        cargo_rol = request.POST.get('cargo_rol')
        motivo_consulta = request.POST.get('motivo_consulta')
        terms = request.POST.get('terms')

        if terms != 'on':
            return JsonResponse({"message": "Debe aceptar los términos y condiciones"}, status=400)

        asunto = "Solicitud de demostración gratuita"
        mensaje = f"""
        Nombre Completo: {nombre_completo}
        Correo Electrónico: {correo_electronico}
        Teléfono: {telefono}
        Nombre de la Empresa: {nombre_empresa}
        Cargo/Rol: {cargo_rol}
        Motivo de la Consulta: {motivo_consulta}
        """
        try:
            send_mail(
                asunto,
                mensaje,
                correo_electronico, 
                ['Contactoigniteconsultor@gmail.com'], 
                fail_silently=False,
            )
            return JsonResponse({"message": "Formulario enviado correctamente. ¡Gracias por tu interés!"})
        except Exception as e:
            return JsonResponse({"message": f"Hubo un error al enviar el correo: {e}"}, status=500)

    return render(request, 'contacto.html')

@csrf_exempt
def get_radar_data(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Método no permitido"}, status=405)
    try:
        data = json.loads(request.body or b'{}')

        # Validar campos
        required_fields = ['ciudad', 'distrito', 'barrio', 'tipo_vivienda',
                          'm2', 'num_habitaciones', 'num_banos', 'precio_esperado',
                          'terraza', 'balcon', 'ascensor']
        for field in required_fields:
            if field not in data:
                return JsonResponse({"error": f"Campo faltante: {field}"}, status=400)
        
        # Obtener datos
        radar_data = PredictionModel.get_radar_data(
            ciudad=data['ciudad'],
            distrito=data['distrito'],
            barrio=data['barrio'],
            tipo_vivienda=int(data['tipo_vivienda']),
            user_data={
                "m2": data['m2'],
                "num_habitaciones": data['num_habitaciones'],
                "num_banos": data['num_banos'],
                "precio_medio": data['precio_esperado'],
                "terraza": data['terraza'],
                "balcon": data['balcon'],
                "ascensor": data['ascensor']
            }
        )
        
        return JsonResponse(radar_data)
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
def formulario_vivienda(request):
    return render(request, 'crear_vivienda.html')
User = get_user_model()

@csrf_exempt
def crear_vivienda_api(request):
    if request.method == 'POST':
        print("📩 Recibido POST en /api/vivienda/")
        m2 = request.POST.get("metros_cuadrados")
        hab = request.POST.get("habitaciones")
        banos = request.POST.get("banos")
        ascensor = request.POST.get("ascensor") == "true"

        descripcion = generar_descripcion_vivienda(m2, hab, banos, ascensor)

        vivienda = Vivienda.objects.create(
            metros_cuadrados=m2,
            habitaciones=hab,
            banos=banos,
            ascensor=ascensor,
            descripcion=descripcion
        )

        for file in request.FILES.getlist("imagenes[]"):
            ImagenVivienda.objects.create(vivienda=vivienda, imagen=file)
        
        imagenes = [img.imagen.path for img in vivienda.imagenes.all()]
        ruta_pdf = generar_pdf(vivienda, imagenes)
        
        try:
            usuario = request.user


            ruta_relativa = ruta_pdf.replace('/media/', '')
            ruta_completa = os.path.join(settings.MEDIA_ROOT, ruta_relativa)

            with open(ruta_completa, 'rb') as f:
                informe = Informe.objects.create(
                    usuario=usuario,
                    archivo_pdf=File(f, name=os.path.basename(ruta_relativa))
        )
        except Exception as e:
            print(f"❌ Error al guardar informe: {e}")

        return JsonResponse({
            "ok": True,
            "mensaje": "Reporte generado",
            "descripcion": descripcion,
            "pdf_url": ruta_pdf
        })
    return JsonResponse({"error": "Método no permitido"}, status=405)

@csrf_exempt
def enviar_vivienda_email(request):
    if request.method == 'POST':
        print("📩 Recibido POST en /api/vivienda/")
        m2 = request.POST.get("metros_cuadrados")
        hab = request.POST.get("habitaciones")
        banos = request.POST.get("banos")
        ascensor = request.POST.get("ascensor") == "true"

        descripcion = generar_descripcion_vivienda(m2, hab, banos, ascensor)

        vivienda = Vivienda.objects.create(
            metros_cuadrados=m2,
            habitaciones=hab,
            banos=banos,
            ascensor=ascensor,
            descripcion=descripcion
        )

        for file in request.FILES.getlist("imagenes[]"):
            ImagenVivienda.objects.create(vivienda=vivienda, imagen=file)
        
        imagenes = [img.imagen.path for img in vivienda.imagenes.all()]
        ruta_pdf = generar_pdf(vivienda, imagenes)
        
        try:
            usuario = request.user
            email = usuario.email 
            ruta_relativa = ruta_pdf.replace('/media/', '')
            ruta_completa = os.path.join(settings.MEDIA_ROOT, ruta_relativa)
            with open(ruta_completa, 'rb') as f:
                pdf_content = f.read()

            email_message = EmailMessage(
                subject='🏠 Informe de Vivienda Generado',
                body=f'Estimado/a {usuario.nombre},\n\nAdjunto encontrarás el informe PDF generado automáticamente con la descripción de tu vivienda.\n\n{descripcion}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            email_message.attach('informe_vivienda.pdf', pdf_content, 'application/pdf')
            email_message.send()


        except Exception as e:
            print("Error al guardar informe")

        return JsonResponse({
            "ok": True,
            "mensaje": "Reporte generado",
            "descripcion": descripcion,
            "pdf_url": ruta_pdf
        })
    return JsonResponse({"error": "Método no permitido"}, status=405)
def generar_descripcion_vivienda(m2, hab, banos, ascensor):
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY no configurado en settings/.env')
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un experto en ventas inmobiliarias."},
            {"role": "user", "content": f"Genera una descripción atractiva para un anuncio de vivienda con {m2}m2, {hab} habitaciones, {banos} baños y {'con' if ascensor else 'sin'} ascensor."}
        ],
        stream=False
    )
    return response.choices[0].message.content
from django.contrib.auth.views import LogoutView

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('home:home')
    http_method_names = ['get', 'post'] 