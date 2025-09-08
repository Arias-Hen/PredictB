from django.contrib import admin
from .models import *

# ------------------------------
# Modelo Valoracion
# ------------------------------
@admin.register(Valoracion)
class ValoracionAdmin(admin.ModelAdmin):
    list_display = (
        'idv', 'iduser', 'modo', 'ciudad', 'distrito', 'barrio', 'calle',
        'tipo_vivienda', 'metros_cuadrados', 'num_habitaciones', 'num_banos',
        'planta', 'terraza', 'balcon', 'ascensor', 'estado_inmueble',
        'fecha_guardado', 'precio_minimo', 'precio_esperado', 'precio_maximo',
        'precio_esperado_unico'
    )
    search_fields = ('ciudad', 'distrito', 'barrio', 'calle', 'modo')
    list_filter = ('ciudad', 'distrito', 'barrio', 'modo', 'estado_inmueble')


# ------------------------------
# Modelo Users (Custom User)
# ------------------------------
@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ('uniqueid', 'usuario', 'email', 'empresa', 'nombre', 'estado', 'is_active', 'is_staff')
    search_fields = ('usuario', 'email', 'nombre', 'empresa')
    list_filter = ('estado', 'is_active', 'is_staff', 'empresa')
    ordering = ('uniqueid',)


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
    list_display = ('usuario', 'archivo_pdf', 'fecha_creacion')  # columnas que se muestran
    list_filter = ('fecha_creacion',)  # filtros en barra lateral
    search_fields = ('usuario__username', 'usuario__email')  # búsqueda por usuario
# ------------------------------
# Modelo ImagenVivienda
# ------------------------------
@admin.register(ImagenVivienda)
class ImagenViviendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'vivienda', 'imagen')
    search_fields = ('vivienda__id',)