# home/signals.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import psycopg2
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
import numpy as np
import joblib
import pandas as pd
from functools import lru_cache
class Task(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_created = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.title

class UsersManager(BaseUserManager):
    def create_user(self, usuario, password=None, **extra_fields):
        if not usuario:
            raise ValueError("El nombre de usuario debe ser proporcionado")
        user = self.model(usuario=usuario, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, usuario, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        return self.create_user(usuario, password, **extra_fields)


class Users(AbstractBaseUser, PermissionsMixin):
    uniqueid = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    empresa = models.CharField(max_length=100, default='Mi Empresa')
    nombre = models.CharField(max_length=100)
    estado = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)    
    last_login = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions',
        blank=True,
    )

    objects = UsersManager()

    USERNAME_FIELD = 'usuario'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'usuarios'

    def __str__(self):
        return self.usuario
    
class Valoracion(models.Model):
    idv = models.AutoField(primary_key=True)
    # FK lógico hacia Users(uniqueid). db_constraint=False evita tocar el schema en Neon,
    # donde la tabla `ventas` se gestiona manualmente.
    iduser = models.ForeignKey(
        'home.Users',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='iduser',
        db_constraint=False,
        related_name='valoraciones',
    )
    modo = models.CharField(max_length=50)
    ciudad = models.CharField(max_length=100)
    distrito = models.CharField(max_length=100)
    barrio = models.CharField(max_length=100)
    calle = models.CharField(max_length=100)
    tipo_vivienda = models.CharField(max_length=100)
    metros_cuadrados = models.FloatField()
    num_habitaciones = models.IntegerField()
    num_banos = models.IntegerField()
    planta = models.IntegerField()
    terraza = models.BooleanField()
    balcon = models.BooleanField()
    ascensor = models.BooleanField()
    estado_inmueble = models.CharField(max_length=50)
    fecha_guardado = models.DateTimeField(auto_now_add=True)
    precio_minimo = models.FloatField()
    precio_esperado = models.FloatField()
    precio_maximo = models.FloatField()
    precio_esperado_unico= models.FloatField()
    correccion_manual = models.BooleanField(default=False)
    precio_corregido = models.FloatField(null=True, blank=True)
    class Meta:
        db_table = 'ventas'

# models.py
class PredictionModel:
    @staticmethod
    def get_radar_data(ciudad, distrito, barrio, tipo_vivienda, user_data):
        conn = None
        try:
            conn = psycopg2.connect(
                host=settings.DATABASES['default']['HOST'],
                port=settings.DATABASES['default']['PORT'],
                database=settings.DATABASES['default']['NAME'],
                user=settings.DATABASES['default']['USER'],
                password=settings.DATABASES['default']['PASSWORD']
            )
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        promedio_m2, promedio_habitaciones, promedio_banos, 
                        promedio_precio, proporcion_terraza, proporcion_balcon, 
                        proporcion_ascensor
                    FROM data.inv_agrupacion_viviendas_madrid
                    WHERE ciudad = %s AND distrito = %s AND barrio = %s AND tipo_vivienda = %s
                """, (ciudad, distrito, barrio, tipo_vivienda))
                
                result = cursor.fetchone()
                
                # Función de escalado idéntica a Streamlit
                def min_max_scaler(arr, max_value, min_val=0, max_val=100):
                    safe_max = max_value if max_value != 0 else 1e-10
                    return min_val + (arr / safe_max) * (max_val - min_val)

                # Procesar datos medios
                valores_medios = {
                    "m2": float(result[0]) if result else 0.0,
                    "habitaciones": float(result[1]) if result else 0.0,
                    "banos": float(result[2]) if result else 0.0,
                    "precio": float(result[3]) if result else 0.0,
                    "terraza": float(result[4]) if result else 0.0,
                    "balcon": float(result[5]) if result else 0.0,
                    "ascensor": float(result[6]) if result else 0.0
                }

                # Procesar datos del usuario
                user_data_float = {
                    "m2": float(user_data.get("m2", 0)),
                    "habitaciones": float(user_data.get("num_habitaciones", 0)),
                    "banos": float(user_data.get("num_banos", 0)),
                    "precio": float(user_data.get("precio_medio", 0)),
                    "terraza": float(user_data.get("terraza", 0)),
                    "balcon": float(user_data.get("balcon", 0)),
                    "ascensor": float(user_data.get("ascensor", 0))
                }

                # Calcular máximos para escalado
                max_values = {
                    'm2': max(valores_medios['m2'], user_data_float['m2']),
                    'habitaciones': max(valores_medios['habitaciones'], user_data_float['habitaciones']),
                    'banos': max(valores_medios['banos'], user_data_float['banos']),
                    'precio': max(valores_medios['precio'], user_data_float['precio'])
                }

                # Aplicar escalado
                scaled_medio = {
                    'm2': min_max_scaler(valores_medios['m2'], max_values['m2']),
                    'habitaciones': min_max_scaler(valores_medios['habitaciones'], max_values['habitaciones']),
                    'banos': min_max_scaler(valores_medios['banos'], max_values['banos']),
                    'precio': min_max_scaler(valores_medios['precio'], max_values['precio'])
                }

                scaled_usuario = {
                    'm2': min_max_scaler(user_data_float['m2'], max_values['m2']),
                    'habitaciones': min_max_scaler(user_data_float['habitaciones'], max_values['habitaciones']),
                    'banos': min_max_scaler(user_data_float['banos'], max_values['banos']),
                    'precio': min_max_scaler(user_data_float['precio'], max_values['precio'])
                }

                return {
                    "valores_medios": scaled_medio,
                    "valores_usuario": scaled_usuario,
                    "texto_adicional": {
                        "porcentajes_barrio": {
                            "terraza": f"{valores_medios['terraza'] * 100:.0f}%",
                            "balcon": f"{valores_medios['balcon'] * 100:.0f}%",
                            "ascensor": f"{valores_medios['ascensor'] * 100:.0f}%"
                        }
                    }
                }
                
        except Exception as e:
            print(f"Error: {str(e)}")
            return {"error": str(e)}
        finally:
            if conn:
                conn.close()

    @staticmethod
    def predict(data):
        ciudad = data.get("ciudad")
        distrito = data.get("distrito")
        barrio = data.get("barrio")
        tipo_vivienda = int(data.get("tipo_vivienda"))
        m2 = float(data.get("m2"))
        num_habitaciones = int(data.get("num_habitaciones"))
        num_banos = int(data.get("num_banos"))
        planta = int(data.get("planta", 0))
        terraza = int(data.get("terraza", 0))
        balcon = int(data.get("balcon", 0))
        ascensor = int(data.get("ascensor", 0))
        estado = data.get("estado")

        df_ciudad = load_csv("distritos.csv")
        df_disbar = load_csv("distrito_barrio.csv")

        ciudad_filtro = df_ciudad[df_ciudad["ciudad"] == ciudad]
        if ciudad_filtro.empty:
            raise ValueError(f"Ciudad '{ciudad}' no encontrada en distritos.csv")
        distrito_filtro = ciudad_filtro[ciudad_filtro["distrito"] == distrito]
        if distrito_filtro.empty:
            raise ValueError(f"Distrito '{distrito}' no encontrado para ciudad '{ciudad}'")
        distrito_val = distrito_filtro["precio_m2_distrito"].values[0]

        barrio_filtro = df_disbar[df_disbar["distrito"] == distrito]
        barrio_filtro = barrio_filtro[barrio_filtro["barrio"] == barrio]
        if barrio_filtro.empty:
            raise ValueError(f"Barrio '{barrio}' no encontrado para distrito '{distrito}'")
        barrio_val = barrio_filtro["precio_m2_barrio"].values[0]

        if tipo_vivienda not in [2, 5, 6]:
            X_list = [
                m2, float(distrito_val), float(barrio_val),
                tipo_vivienda, num_habitaciones, num_banos,
                planta, terraza, balcon, ascensor, estado,
            ]
            model_path = settings.BASE_DIR / 'modelos' / 'modelo_rf_pisos_joblib.pkl'
        else:
            X_list = [
                m2, float(distrito_val), float(barrio_val),
                tipo_vivienda, num_habitaciones, num_banos,
            ]
            model_path = settings.BASE_DIR / 'modelos' / 'modelo_rf_casas_joblib.pkl'

        if not model_path.exists():
            raise FileNotFoundError(f"Modelo joblib no encontrado en {model_path}")

        X = np.array(X_list, dtype=np.float64).reshape(1, -1)
        model = _load_model(str(model_path))

        predicciones = model.predict(X)

        corrector = 0.10
        predicciones_bottom = predicciones * (1 - 2 * corrector)
        precio_medio = predicciones * (1 - corrector)
        predicciones_top = predicciones

        return {
            "precio_minimo": np.round(predicciones_bottom[0], 2),
            "precio_esperado": np.round(precio_medio[0], 2),
            "precio_maximo": np.round(predicciones_top[0], 2),
        }

class Vivienda(models.Model):
    metros_cuadrados = models.PositiveIntegerField()
    habitaciones = models.PositiveIntegerField()
    banos = models.PositiveIntegerField()
    ascensor = models.BooleanField()
    descripcion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Vivienda {self.id} - {self.metros_cuadrados} m2"

class ImagenVivienda(models.Model):
    vivienda = models.ForeignKey(Vivienda, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='viviendas/')

    def __str__(self):
        return f"Imagen de Vivienda {self.vivienda.id}"
    
User = get_user_model()
class Informe(models.Model):
    TIPO_CHOICES = (('informe', 'Informe'), ('dossier', 'Dossier'))

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    archivo_pdf = models.FileField(upload_to='informes/')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='informe')
    # Valoración de origen (para mostrar ubicación/precio en la vista Informes).
    valoracion = models.ForeignKey(
        'Valoracion', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='informes', db_constraint=False,
    )

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.usuario} - {self.fecha_creacion.strftime('%Y-%m-%d')}"


    class Meta:
        db_table = 'informes'


class Ciudad(models.Model):
    nombre = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'ciudades'
        verbose_name_plural = 'ciudades'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Distrito(models.Model):
    ciudad = models.ForeignKey(Ciudad, on_delete=models.CASCADE, related_name='distritos')
    nombre = models.CharField(max_length=255)
    precio_m2 = models.FloatField(null=True, default=0, blank=True)

    class Meta:
        db_table = 'distritos'
        verbose_name_plural = 'distritos'
        ordering = ['nombre']
        unique_together = ['nombre', 'ciudad']

    def __str__(self):
        return f"{self.nombre} ({self.ciudad.nombre})"


class Barrio(models.Model):
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE, related_name='barrios')
    nombre = models.CharField(max_length=255)
    precio_m2 = models.FloatField(null=True, default=0, blank=True)

    class Meta:
        db_table = 'barrios'
        verbose_name_plural = 'barrios'
        ordering = ['nombre']
        unique_together = ['nombre', 'distrito']

    def __str__(self):
        return f"{self.nombre} ({self.distrito.nombre})"


class Calle(models.Model):
    nombre = models.CharField(max_length=255)
    barrio = models.ForeignKey(Barrio, on_delete=models.CASCADE, related_name='calles')
    precio_m2 = models.FloatField(null=True, default=0, blank=True)

    class Meta:
        db_table = 'calles'
        verbose_name_plural = 'calles'
        ordering = ['nombre']
        unique_together = ['nombre', 'barrio']

    def __str__(self):
        return f"{self.nombre}, {self.barrio.nombre} ({self.barrio.distrito.nombre})"


def load_csv(file_name):
    path = settings.BASE_DIR / 'home' / 'csv' / file_name
    return pd.read_csv(path, encoding='ISO-8859-1')


@lru_cache(maxsize=4)
def _load_model(model_path):
    return joblib.load(model_path)