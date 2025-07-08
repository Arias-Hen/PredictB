from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import psycopg2
from django.conf import settings

class Task(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_created = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created']

    def _str_(self):
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
    empresa = models.CharField(max_length=100, default='Mi Empresa')
    nombre = models.CharField(max_length=100)
    estado = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',  # Nombre único para evitar conflictos
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions',  # Nombre único para evitar conflictos
        blank=True,
    )

    objects = UsersManager()

    USERNAME_FIELD = 'usuario'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'data"."users'

    def __str__(self):
        return self.usuario
    
class Valoracion(models.Model):
    idv = models.AutoField(primary_key=True)
    iduser = models.IntegerField()
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
    class Meta:
        db_table = 'data"."ventas'

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