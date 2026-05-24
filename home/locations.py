"""
Lectura cacheada de los CSV de ubicaciones (ciudad → distrito → barrio → calle).

Antes cada request abría los CSV completos. Aquí se leen una vez por proceso
con lru_cache. Si necesitas refrescar (CSV cambió en disco), llama a `clear_cache()`.
"""
import csv
from functools import lru_cache
from django.conf import settings

ENCODING = 'ISO-8859-1'


@lru_cache(maxsize=8)
def _read_csv(filename):
    path = settings.BASE_DIR / filename
    with open(path, newline='', encoding=ENCODING) as f:
        return list(csv.DictReader(f))


def ciudades():
    return sorted({r['ciudad'] for r in _read_csv('distritos.csv') if r.get('ciudad')})


def distritos(ciudad):
    return sorted({
        r['distrito']
        for r in _read_csv('distritos.csv')
        if r.get('ciudad') == ciudad and r.get('distrito')
    })


def barrios(distrito):
    return sorted({
        r['barrio']
        for r in _read_csv('distrito_barrio.csv')
        if r.get('distrito') == distrito and r.get('barrio')
    })


def calles(barrio):
    seen = set()
    out = []
    for r in _read_csv('tb_todo_precio_m2.csv'):
        if r.get('barrio') == barrio and (calle := r.get('calle')) and calle not in seen:
            seen.add(calle)
            out.append(calle)
    return sorted(out)


def clear_cache():
    _read_csv.cache_clear()
