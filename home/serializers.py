from rest_framework import serializers
from django.contrib.auth.hashers import make_password

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

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': 'Requerido al crear usuario'})
        validated_data['password'] = make_password(password)
        return Users.objects.create(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ValoracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Valoracion
        fields = '__all__'
        read_only_fields = ('idv', 'fecha_guardado')


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
    usuario_nombre = serializers.CharField(source='usuario.nombre', read_only=True)
    usuario_email = serializers.CharField(source='usuario.email', read_only=True)
    archivo_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Informe
        fields = (
            'id', 'usuario', 'usuario_nombre', 'usuario_email',
            'archivo_pdf', 'archivo_pdf_url', 'fecha_creacion',
        )
        read_only_fields = ('id', 'fecha_creacion')

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