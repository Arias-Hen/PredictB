import csv
from django.core.management.base import BaseCommand
from django.conf import settings
from home.models import Ciudad, Distrito, Barrio, Calle

CSV_DIR = settings.BASE_DIR / 'home' / 'csv'
ENCODING = 'ISO-8859-1'

def _read_csv(filename):
    path = CSV_DIR / filename
    with open(path, newline='', encoding=ENCODING) as f:
        return list(csv.DictReader(f))


class Command(BaseCommand):
    help = 'Importa ubicaciones desde CSV a la base de datos'

    def handle(self, *args, **options):
        # 1. Ciudades + Distritos
        for row in _read_csv('distritos.csv'):
            ciudad, _ = Ciudad.objects.get_or_create(nombre=row['ciudad'])
            Distrito.objects.get_or_create(
                nombre=row['distrito'],
                ciudad=ciudad,
                defaults={'precio_m2': row['precio_m2_distrito']}
            )
        self.stdout.write(self.style.SUCCESS('Distritos importados'))

        # 2. Barrios (desde tb_todo_precio_m2.csv que incluye ciudad)
        seen_barrios = set()
        for row in _read_csv('tb_todo_precio_m2.csv'):
            key = (row['ciudad'], row['distrito'], row['barrio'])
            if key in seen_barrios:
                continue
            seen_barrios.add(key)
            distrito = Distrito.objects.get(nombre=row['distrito'], ciudad__nombre=row['ciudad'])
            Barrio.objects.get_or_create(
                nombre=row['barrio'],
                distrito=distrito,
                defaults={'precio_m2': row['precio_m2_barrio']}
            )
        self.stdout.write(self.style.SUCCESS('Barrios importados'))

        # 3. Calles (deduplicando)
        seen_calles = set()
        for row in _read_csv('tb_todo_precio_m2.csv'):
            key = (row['barrio'], row['calle'])
            if key in seen_calles:
                continue
            seen_calles.add(key)
            distrito = Distrito.objects.get(nombre=row['distrito'], ciudad__nombre=row['ciudad'])
            barrio = Barrio.objects.get(nombre=row['barrio'], distrito=distrito)
            Calle.objects.get_or_create(
                nombre=row['calle'],
                barrio=barrio,
                defaults={'precio_m2': row['precio_m2_calle']}
            )
        self.stdout.write(self.style.SUCCESS('Calles importadas'))
