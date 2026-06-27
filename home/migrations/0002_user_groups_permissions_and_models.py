"""
Añade los M2M groups/user_permissions a Users (ahora sí puede depender de auth),
y crea el resto de modelos.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("home", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="users",
            name="groups",
            field=models.ManyToManyField(
                blank=True, related_name="custom_user_set", to="auth.group"
            ),
        ),
        migrations.AddField(
            model_name="users",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True, related_name="custom_user_permissions", to="auth.permission"
            ),
        ),
        migrations.CreateModel(
            name="Vivienda",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("metros_cuadrados", models.PositiveIntegerField()),
                ("habitaciones", models.PositiveIntegerField()),
                ("banos", models.PositiveIntegerField()),
                ("ascensor", models.BooleanField()),
                ("descripcion", models.TextField(blank=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Informe",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("archivo_pdf", models.FileField(upload_to="informes/")),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "informes"},
        ),
        migrations.CreateModel(
            name="Valoracion",
            fields=[
                ("idv", models.AutoField(primary_key=True, serialize=False)),
                ("modo", models.CharField(max_length=50)),
                ("ciudad", models.CharField(max_length=100)),
                ("distrito", models.CharField(max_length=100)),
                ("barrio", models.CharField(max_length=100)),
                ("calle", models.CharField(max_length=100)),
                ("tipo_vivienda", models.CharField(max_length=100)),
                ("metros_cuadrados", models.FloatField()),
                ("num_habitaciones", models.IntegerField()),
                ("num_banos", models.IntegerField()),
                ("planta", models.IntegerField()),
                ("terraza", models.BooleanField()),
                ("balcon", models.BooleanField()),
                ("ascensor", models.BooleanField()),
                ("estado_inmueble", models.CharField(max_length=50)),
                ("fecha_guardado", models.DateTimeField(auto_now_add=True)),
                ("precio_minimo", models.FloatField()),
                ("precio_esperado", models.FloatField()),
                ("precio_maximo", models.FloatField()),
                ("precio_esperado_unico", models.FloatField()),
                (
                    "iduser",
                    models.ForeignKey(
                        blank=True,
                        db_column="iduser",
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="valoraciones",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "ventas"},
        ),
        migrations.CreateModel(
            name="ImagenVivienda",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("imagen", models.ImageField(upload_to="viviendas/")),
                (
                    "vivienda",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="imagenes",
                        to="home.vivienda",
                    ),
                ),
            ],
        ),
    ]
