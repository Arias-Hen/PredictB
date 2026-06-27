"""
Consultas de ubicaciones desde la base de datos (modelos ORM).
Reemplaza la lectura directa de CSVs para mejor performance con índices.
"""
from home.models import Ciudad, Distrito, Barrio, Calle


def ciudades():
    return list(Ciudad.objects.values_list('nombre', flat=True).order_by('nombre'))


def distritos(ciudad_nombre):
    return list(
        Distrito.objects.filter(ciudad__nombre=ciudad_nombre)
        .values_list('nombre', flat=True)
        .order_by('nombre')
    )


def barrios(distrito_nombre):
    return list(
        Barrio.objects.filter(distrito__nombre=distrito_nombre)
        .values_list('nombre', flat=True)
        .order_by('nombre')
    )


def calles(barrio_nombre):
    return list(
        Calle.objects.filter(barrio__nombre=barrio_nombre)
        .values_list('nombre', flat=True)
        .order_by('nombre')
    )
