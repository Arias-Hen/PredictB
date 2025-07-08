from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
app_name = 'home'

urlpatterns = [
    path('', views.home, name='home'),
    path('inicio/', views.inicio, name='inicio'),
    path('cfunciona/', views.cfunciona, name='cfunciona'),
    path('casos/', views.casos, name='casos'),
    path('contacto/', views.contacto, name='contacto'),
    path('valoraciones/', views.valoraciones, name='valoraciones'),
    path('ventas/', views.ventas, name='ventas'),
    path('informes/', views.informes, name='informes'),
    path('generarinf/', views.generarinf, name='generarinf'),
    path('get_distritos/<str:ciudad>/', views.get_distritos, name='get_distritos'),
    path('get_barrios/<str:distrito>/', views.get_barrios, name='get_barrios'),
    path('get_calles/<str:barrios>/', views.get_calles, name='get_calles'),
    path('guardar_valoracion/', views.guardar_valoracion, name='get_guardar_valoracion'),
    path('modificar_valoracion/', views.modificar_valoracion, name='get_modificar_valoracion'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('exportar_excel/', views.exportar_excel, name='exportar_excel'),
    path('terminos/', views.terminos, name='terminos'),
    path('get_radar_data/', views.get_radar_data, name='get_radar_data'),
    path('c_vivienda', views.formulario_vivienda, name='formulario_vivienda'),
    path('api/vivienda/', views.crear_vivienda_api, name='crear_vivienda_api'),

]