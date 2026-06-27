from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import Users, Valoracion, Informe, Vivienda, ImagenVivienda


class UsersSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Users
        fields = (
            'uniqueid', 'usuario', 'email', 'empresa', 'nombre',
            'estado', 'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login', 'password',
        )
        read_only_fields = ('uniqueid', 'date_joined', 'last_login')

    def _validar_password(self, password, user=None):
        """Valida la contraseña con AUTH_PASSWORD_VALIDATORS y la devuelve."""
        try:
            validate_password(password, user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)})
        return password

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': 'Requerido al crear usuario'})
        self._validar_password(password, Users(**{
            k: v for k, v in validated_data.items()
            if k in ('usuario', 'email', 'nombre')
        }))
        validated_data['password'] = make_password(password)
        return Users.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # Permite al admin editar datos y/o contraseña en una sola petición
        # (PATCH desde el modal de edición). La contraseña es opcional.
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            self._validar_password(password, instance)
            instance.set_password(password)
        instance.save()
        return instance


class ValoracionSerializer(serializers.ModelSerializer):
    # Datos legibles del autor de la valoración. `iduser` por sí solo serializa
    # únicamente el ID numérico; el panel admin necesita identificar al usuario.
    usuario = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Valoracion
        fields = '__all__'
        # iduser (dueño) lo fija la vista con el usuario logueado; nunca debe venir
        # del payload, o un usuario podría reasignar su valoración a otro vía PUT/PATCH.
        read_only_fields = ('idv', 'fecha_guardado', 'iduser')

    def get_usuario(self, obj):
        u = obj.iduser
        if not u:
            return None
        return {
            'id': u.uniqueid,
            'usuario': u.usuario,
            'nombre': u.nombre,
            'email': u.email,
            'empresa': u.empresa,
        }


class ViviendaSerializer(serializers.ModelSerializer):
    imagenes = serializers.SerializerMethodField()

    class Meta:
        model = Vivienda
        fields = (
            'id', 'metros_cuadrados', 'habitaciones', 'banos',
            'ascensor', 'descripcion', 'fecha_creacion', 'imagenes',
        )
        read_only_fields = ('id', 'fecha_creacion')

    def get_imagenes(self, obj):
        request = self.context.get('request')
        return [
            request.build_absolute_uri(img.imagen.url) if request else img.imagen.url
            for img in obj.imagenes.all()
        ]


class ImagenViviendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenVivienda
        fields = ('id', 'vivienda', 'imagen')


class InformeSerializer(serializers.ModelSerializer):
    # Datos legibles del autor del informe — mismo formato anidado que
    # ValoracionSerializer, para que el panel admin identifique al usuario.
    usuario = serializers.SerializerMethodField(read_only=True)
    # Para crear/asignar el informe a un usuario (POST en el panel admin).
    usuario_id = serializers.PrimaryKeyRelatedField(
        source='usuario', queryset=Users.objects.all(), write_only=True,
    )
    archivo_pdf_url = serializers.SerializerMethodField()
    # Datos derivados de la valoración de origen, para la tabla de Informes.
    ubicacion = serializers.SerializerMethodField()
    precio = serializers.SerializerMethodField()

    class Meta:
        model = Informe
        fields = (
            'id', 'usuario', 'usuario_id', 'tipo', 'valoracion',
            'ubicacion', 'precio',
            'archivo_pdf', 'archivo_pdf_url', 'fecha_creacion',
        )
        read_only_fields = ('id', 'fecha_creacion')

    def get_ubicacion(self, obj):
        v = obj.valoracion
        if not v:
            return None
        return ', '.join([p for p in [v.barrio, v.ciudad] if p]) or None

    def get_precio(self, obj):
        v = obj.valoracion
        return v.precio_esperado if v else None

    def get_usuario(self, obj):
        u = obj.usuario
        if not u:
            return None
        return {
            'id': u.uniqueid,
            'usuario': u.usuario,
            'nombre': u.nombre,
            'email': u.email,
            'empresa': u.empresa,
        }

    def get_archivo_pdf_url(self, obj):
        if not obj.archivo_pdf:
            return None
        request = self.context.get('request')
        url = obj.archivo_pdf.url
        return request.build_absolute_uri(url) if request else url
class PredictionInputSerializer(serializers.Serializer):
    ciudad = serializers.CharField()
    distrito = serializers.CharField()
    barrio = serializers.CharField()
    tipo_vivienda = serializers.CharField()
    m2 = serializers.FloatField()
    num_habitaciones = serializers.IntegerField()
    num_banos = serializers.IntegerField()
    planta = serializers.IntegerField()
    terraza = serializers.IntegerField()
    balcon = serializers.IntegerField()
    ascensor = serializers.IntegerField()
    estado = serializers.IntegerField()