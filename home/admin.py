from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.urls import path
from django.contrib import messages
from django.core.cache import cache
import json

def clean_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    value = str(value).lower()
    if value == 'true':
        return True
    if value == 'false':
        return False
    return None


# ======================================================
# MODELO VALORACION

@admin.register(Valoracion)
class ValoracionAdmin(admin.ModelAdmin):

    list_per_page = 50
    show_full_result_count = False

    list_display = (
        'idv', 'iduser', 'modo', 'ciudad', 'distrito', 'barrio', 'calle',
        'get_tipo_vivienda_text',
        'metros_cuadrados', 'num_habitaciones', 'num_banos',
        'planta', 'terraza', 'balcon', 'ascensor',
        'get_estado_inmueble',
        'fecha_guardado', 'precio_minimo',
        'precio_esperado', 'precio_maximo',
        'precio_esperado_unico'
    )

    change_list_template = 'admin/home/valoracion/change_list.html'

    # ---------- CACHE CIUDADES ----------
    def get_ciudades(self):
        key = 'valoracion_ciudades'
        data = cache.get(key)
        if data is None:
            data = list(
                Valoracion.objects
                .exclude(ciudad__isnull=True)
                .exclude(ciudad='')
                .values_list('ciudad', flat=True)
                .distinct()
            )
            cache.set(key, data, 3600)
        return data

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['options_json'] = json.dumps(
            [{'id': c, 'name': c} for c in self.get_ciudades()]
        )
        extra_context['context_json'] = json.dumps({
            'ciudad': request.GET.get('ciudad') or None,
            'distrito': request.GET.get('distrito') or None,
            'barrio': request.GET.get('barrio') or None,
            'calle': request.GET.get('calle') or None,
            'modo': request.GET.get('modo') or None,
        })
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('get_distritos/<str:ciudad>/', self.admin_site.admin_view(self.get_distritos)),
            path('get_barrios/<str:distrito>/', self.admin_site.admin_view(self.get_barrios)),
            path('get_calles/<str:barrio>/', self.admin_site.admin_view(self.get_calles)),
        ]
        return custom_urls + urls

    def _cached_distinct(self, key, qs, field):
        data = cache.get(key)
        if data is None:
            data = list(
                qs.exclude(**{f'{field}__isnull': True})
                  .exclude(**{field: ''})
                  .values_list(field, flat=True)
                  .distinct()
            )
            cache.set(key, data, 3600)
        return data

    def get_distritos(self, request, ciudad):
        data = self._cached_distinct(
            f'distritos_{ciudad}',
            Valoracion.objects.filter(ciudad=ciudad),
            'distrito'
        )
        return JsonResponse({'distritos': [{'id': d, 'name': d} for d in data]})

    def get_barrios(self, request, distrito):
        data = self._cached_distinct(
            f'barrios_{distrito}',
            Valoracion.objects.filter(distrito=distrito),
            'barrio'
        )
        return JsonResponse({'barrio': [{'id': b, 'name': b} for b in data]})

    def get_calles(self, request, barrio):
        data = self._cached_distinct(
            f'calles_{barrio}',
            Valoracion.objects.filter(barrio=barrio),
            'calle'
        )
        return JsonResponse({'calle': [{'id': c, 'name': c} for c in data]})

    # ---------- DISPLAY ----------
    @admin.display(description="Tipo de Vivienda",
    ordering="tipo_vivienda")
    def get_tipo_vivienda_text(self, obj):
        return {
            '0': 'Estudio',
            '1': 'Piso',
            '2': 'Chalet adosado',
            '3': 'Dúplex',
            '4': 'Ático',
            '5': 'Chalet pareado',
            '6': 'Casa o chalet',
        }.get(str(obj.tipo_vivienda), 'No especificado')
    
    @admin.display(description="Estado del Inmueble",
    ordering="estado_inmueble")
    def get_estado_inmueble(self, obj):
        return {
            '0': 'Obra nueva',
            '1': 'Segunda Mano/buen estado',
            '2': 'Segunda Mano/para reformar',
            '3': 'No declara',
        }.get(str(obj.estado_inmueble), 'No especificado')
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.model._meta.verbose_name_plural = "Valoraciones"


# ======================================================
# MODELO USERS (CUSTOM USER)

User = get_user_model()

class UsersCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('usuario', 'email', 'empresa', 'nombre')


class UsersChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            'usuario', 'email', 'empresa',
            'nombre', 'estado', 'is_active', 'is_staff'
        )


@admin.register(User)
class UsersAdmin(BaseUserAdmin):
    search_fields = ()

    model = User
    add_form = UsersCreationForm
    form = UsersChangeForm

    list_display = (
        'uniqueid', 'usuario', 'email',
        'empresa', 'nombre', 'estado',
        'is_active', 'is_staff'
    )

    ordering = ('uniqueid',)
    list_per_page = 50
    show_full_result_count = False

    actions = ['delete_selected_users']
    actions_on_top = True
    actions_on_bottom = False
    actions_selection_counter = False

    change_list_template = 'admin/home/user/change_list.html'

    readonly_fields = ('last_login', 'date_joined')

    fieldsets = (
        (None, {'fields': ('usuario', 'password')}),
        ('Información personal', {
            'fields': ('email', 'empresa', 'nombre', 'estado')
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Fechas', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    # ---------- CREACIÓN ----------
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'usuario',
                'email',
                'empresa',
                'nombre',
                'estado',
                'password1',
                'password2',
            ),
        }),
    )

    def get_empresas(self):
        key = 'users_empresas'
        data = cache.get(key)
        if data is None:
            data = list(
                User.objects
                .exclude(empresa__isnull=True)
                .exclude(empresa='')
                .values_list('empresa', flat=True)
                .distinct()
            )
            cache.set(key, data, 3600)
        return data

    def get_estados(self):
        key = 'users_estados'
        data = cache.get(key)
        if data is None:
            data = list(
                User.objects
                .values_list('estado', flat=True)
                .distinct()
            )
            cache.set(key, data, 3600)
        return data

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        is_active = clean_bool(request.GET.get('is_active'))
        if is_active is not None:
            qs = qs.filter(is_active=is_active)

        is_staff = clean_bool(request.GET.get('is_staff'))
        if is_staff is not None:
            qs = qs.filter(is_staff=is_staff)

        return qs

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        extra_context['empresas_json'] = json.dumps(
            [{'id': e, 'name': e} for e in self.get_empresas()]
        )

        extra_context['estados_json'] = json.dumps([
            {'id': str(e).lower(), 'name': 'Activo' if e else 'Inactivo'}
            for e in self.get_estados()
        ])

        extra_context['context_json'] = json.dumps({
            'empresa': request.GET.get('empresa') or None,
            'estado': request.GET.get('estado') or None,
            'busqueda': request.GET.get('q') or None,
            'is_active': clean_bool(request.GET.get('is_active')),
            'is_staff': clean_bool(request.GET.get('is_staff')),
        })

        return super().changelist_view(request, extra_context=extra_context)

    #BORRAR
    def delete_selected_users(self, request, queryset):
        deleted = 0
        for user in queryset:
            if user.is_superuser or user == request.user:
                continue
            user.delete()
            deleted += 1
        self.message_user(request, f'{deleted} usuario(s) eliminados correctamente')
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.model._meta.verbose_name_plural = "Usuarios"

@admin.register(Vivienda)
class ViviendaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'metros_cuadrados',
        'habitaciones', 'banos',
        'ascensor', 'fecha_creacion'
    )
    search_fields = ('descripcion',)
    list_filter = ('ascensor', 'habitaciones', 'banos')


@admin.register(Informe)
class InformeAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'archivo_pdf', 'fecha_creacion')
    list_filter = ('fecha_creacion',)
    search_fields = ('usuario', 'usuario__email')


@admin.register(ImagenVivienda)
class ImagenViviendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'vivienda', 'imagen')
    search_fields = ('vivienda__id',)
