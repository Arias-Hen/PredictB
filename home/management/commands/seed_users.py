"""Crea usuarios de prueba: un admin y un usuario normal. Idempotente.

    python manage.py seed_users

Vuelve a fijar la contraseña en cada ejecución, así que sirve también para
"resetear" estos usuarios a su estado conocido.
"""
from django.core.management.base import BaseCommand
from home.models import Users

SEED_USERS = [
    {
        'usuario': 'Ignite123',
        'password': 'Ignite123',
        'nombre': 'Administrador Ignite',
        'email': 'admin@ignite.com',
        'empresa': 'Ignite Labs',
        'is_staff': True,
        'is_superuser': True,
    },
    {
        'usuario': 'will123',
        'password': 'password',
        'nombre': 'Will',
        'email': 'will@example.com',
        'empresa': 'Demo',
        'is_staff': False,
        'is_superuser': False,
    },
]


class Command(BaseCommand):
    help = 'Crea/actualiza usuarios de prueba (admin Ignite123 + usuario will123).'

    def handle(self, *args, **options):
        for spec in SEED_USERS:
            password = spec['password']
            defaults = {k: v for k, v in spec.items() if k not in ('usuario', 'password')}
            user, created = Users.objects.get_or_create(
                usuario=spec['usuario'], defaults={**defaults, 'estado': True, 'is_active': True}
            )
            # Reaplica campos + contraseña aunque ya existiera (reset idempotente).
            for field, value in defaults.items():
                setattr(user, field, value)
            user.set_password(password)
            user.save()
            estado = 'creado' if created else 'actualizado'
            rol = 'ADMIN' if spec['is_staff'] else 'usuario'
            self.stdout.write(self.style.SUCCESS(
                f'{rol:7} {spec["usuario"]:12} / {password:12} -> {estado}'
            ))
