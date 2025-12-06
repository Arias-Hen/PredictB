from django.contrib import admin
from .models import *
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from rangefilter.filters import DateRangeFilter, DateTimeRangeFilter
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter
from .admin_filters import CiudadFilter, DistritoFilter, BarrioFilter, CalleFilter
import json 
from django.http import JsonResponse
from django.urls import path
from django.contrib import messages
# ------------------------------
# Modelo Valoracion
# ------------------------------
@admin.register(Valoracion)
class ValoracionAdmin(admin.ModelAdmin):
    list_display = (
        'idv', 'iduser', 'modo', 'ciudad', 'distrito', 'barrio', 'calle',
        'get_tipo_vivienda_text',
        'metros_cuadrados', 'num_habitaciones', 'num_banos',
        'planta', 'terraza', 'balcon', 'ascensor', 'get_estado_inmueble',
        'fecha_guardado', 'precio_minimo', 'precio_esperado', 'precio_maximo',
        'precio_esperado_unico'
    )
    
    change_list_template = 'admin/home/valoracion/change_list.html'
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        ciudades = Valoracion.objects.values_list('ciudad', flat=True).distinct()
        
        ciudades_options = []
        for i, ciudad in enumerate(ciudades):
            if ciudad:
                ciudades_options.append({
                    'id': ciudad,
                    'name': ciudad
                })
        
        extra_context['options_json'] = json.dumps(ciudades_options)
        
        extra_context['context_json'] = json.dumps({
            'ciudad': request.GET.get('ciudad', ''),
            'distrito': request.GET.get('distrito', ''),
            'barrio': request.GET.get('barrio', ''),
            'calle': request.GET.get('calle', ''),
            'modo': request.GET.get('modo', '')
        })
        
        return super().changelist_view(request, extra_context=extra_context)
    
    def get_urls(self):
        from django.urls import path
        
        urls = super().get_urls()
        custom_urls = [
            path('get_distritos/<str:ciudad>/', self.admin_site.admin_view(self.get_distritos), name='get_distritos'),
            path('get_barrios/<str:distrito>/', self.admin_site.admin_view(self.get_barrios), name='get_barrios'),
            path('get_calles/<str:barrio>/', self.admin_site.admin_view(self.get_calles), name='get_calles'),
        ]
        return custom_urls + urls
    
    def get_distritos(self, request, ciudad):
        distritos = Valoracion.objects.filter(
            ciudad=ciudad
        ).values_list('distrito', flat=True).distinct()
        
        distritos_list = []
        for distrito in distritos:
            if distrito:
                distritos_list.append({
                    'id': distrito,
                    'name': distrito
                })
        
        return JsonResponse({'distritos': distritos_list})
    
    def get_barrios(self, request, distrito):
        barrios = Valoracion.objects.filter(
            distrito=distrito
        ).values_list('barrio', flat=True).distinct()
        
        barrios_list = []
        for barrio in barrios:
            if barrio:
                barrios_list.append({
                    'id': barrio,
                    'name': barrio
                })
        
        return JsonResponse({'barrio': barrios_list})
    
    def get_calles(self, request, barrio):
        calles = Valoracion.objects.filter(
            barrio=barrio
        ).values_list('calle', flat=True).distinct()
        
        calles_list = []
        for calle in calles:
            if calle:
                calles_list.append({
                    'id': calle,
                    'name': calle
                })
        
        return JsonResponse({'calle': calles_list})

    def get_tipo_vivienda_text(self, obj):
        TIPO_VIVIENDA_MAP = {
            '0': 'Estudio',
            '1': 'Piso', 
            '2': 'Chalet adosado',
            '3': 'Dúplex',
            '4': 'Ático',
            '5': 'Chalet pareado',
            '6': 'Casa o chalet',
        }
        
        if obj.tipo_vivienda is None:
            return 'No especificado'
        
        raw_value = str(obj.tipo_vivienda).strip()
        
        return TIPO_VIVIENDA_MAP.get(raw_value, f'❓ Desconocido ({raw_value})')
    
    get_tipo_vivienda_text.short_description = 'Tipo Vivienda'
    get_tipo_vivienda_text.admin_order_field = 'tipo_vivienda'
    
    def get_estado_inmueble(self, obj):
        ESTADO_INMUEBLE_MAP = {
            '0': 'Obra nueva',
            '1': 'Segunda Mano/buen estado',
            '2': 'Segunda Mano/para reformar',
            '3': 'No declara',
        }
        
        if obj.estado_inmueble is None:
            return 'No especificado'
        
        raw_value = str(obj.estado_inmueble).strip()
        
        return ESTADO_INMUEBLE_MAP.get(raw_value, f'❓ Desconocido ({raw_value})')
    
    get_estado_inmueble.short_description = 'Estado Inmueble'
    get_estado_inmueble.admin_order_field = 'estado_inmueble'
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.model._meta.verbose_name_plural = "Valoraciones"


# ------------------------------
# Modelo Users (Custom User)
# ------------------------------
User = get_user_model()

# --- FORMULARIO DE CREACIÓN ---
class UsersCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('usuario', 'email', 'empresa', 'nombre')


# --- FORMULARIO DE EDICIÓN ---
class UsersChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('usuario', 'email', 'empresa', 'nombre', 'estado', 'is_active', 'is_staff')


class UsersAdmin(BaseUserAdmin):
    add_form = UsersCreationForm
    form = UsersChangeForm
    model = User
    list_filter = ()
    search_fields = ()
    list_display = ('uniqueid', 'usuario', 'email', 'empresa', 'nombre', 'estado', 'is_active', 'is_staff')
    ordering = ('uniqueid',)
    actions_on_top = False
    actions_on_bottom = False
    actions_selection_counter = False
    actions = []
    def delete_selected_users(self, request, queryset):
        count = queryset.count()
        deleted_count = 0
        
        for user in queryset:
            if user.is_superuser:
                messages.error(request, f'No se puede eliminar al superusuario {user.usuario}')
                continue
            if user == request.user:
                messages.error(request, 'No puedes eliminarte a ti mismo')
                continue
            user.delete()
            deleted_count += 1
        
        if deleted_count == 1:
            message = "1 usuario fue eliminado exitosamente"
        elif deleted_count > 1:
            message = f"{deleted_count} usuarios fueron eliminados exitosamente"
        else:
            message = "No se eliminó ningún usuario"
        
        self.message_user(request, message)
    
    delete_selected_users.short_description = "Eliminar usuarios seleccionados"
    fieldsets = (
        (None, {'fields': ('usuario', 'password')}),
        ('Información personal', {'fields': ('email', 'empresa', 'nombre', 'estado')}),
        ('Permisos', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('date_joined',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('usuario', 'email', 'password1', 'password2', 'empresa', 'nombre', 'estado'),
        }),
    )
    change_list_template = 'admin/home/user/change_list.html'
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Obtener empresas únicas para filtro
        empresas = User.objects.values_list('empresa', flat=True).distinct()
        empresas_options = [{'id': emp, 'name': emp} for emp in empresas if emp]
        
        # Obtener estados únicos
        estados = User.objects.values_list('estado', flat=True).distinct()
        estados_options = [{'id': est, 'name': est} for est in estados if est]
        
        extra_context['empresas_json'] = json.dumps(empresas_options)
        extra_context['estados_json'] = json.dumps(estados_options)
        extra_context['context_json'] = json.dumps({
            'empresa': request.GET.get('empresa', ''),
            'estado': request.GET.get('estado', ''),
            'busqueda': request.GET.get('q', '')
        })
        
        return super().changelist_view(request, extra_context=extra_context)
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        model._meta.verbose_name_plural = "Usuarios"

admin.site.register(User, UsersAdmin)
# ------------------------------
# Modelo Vivienda
# ------------------------------
@admin.register(Vivienda)
class ViviendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'metros_cuadrados', 'habitaciones', 'banos', 'ascensor', 'fecha_creacion')
    search_fields = ('descripcion',)
    list_filter = ('ascensor', 'habitaciones', 'banos')
# ------------------------------
# Modelo Informe
# ------------------------------

@admin.register(Informe)
class InformeAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'archivo_pdf', 'fecha_creacion')
    list_filter = ('fecha_creacion',)
    search_fields = ('usuario', 'usuario__email') 
# ------------------------------
# Modelo ImagenVivienda
# ------------------------------
@admin.register(ImagenVivienda)
class ImagenViviendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'vivienda', 'imagen')
    search_fields = ('vivienda__id',)