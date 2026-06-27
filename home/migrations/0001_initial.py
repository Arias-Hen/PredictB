"""
Crea solo el modelo Users SIN los M2M a auth, para que las migraciones de
`auth` que referencian AUTH_USER_MODEL puedan correr después de esta.

Patrón estándar de "custom user model done right".
"""
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Users",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                ("uniqueid", models.AutoField(primary_key=True, serialize=False)),
                ("usuario", models.CharField(max_length=100, unique=True)),
                ("email", models.EmailField(blank=True, max_length=254, null=True, unique=True)),
                ("empresa", models.CharField(default="Mi Empresa", max_length=100)),
                ("nombre", models.CharField(max_length=100)),
                ("estado", models.BooleanField(default=True)),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_login", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
            ],
            options={"db_table": "usuarios"},
        ),
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("is_created", models.BooleanField(default=False)),
                ("created", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created"]},
        ),
    ]
