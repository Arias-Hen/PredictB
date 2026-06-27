"""Integraciones de IA (OpenAI).

Aislado del resto de vistas para que la API no dependa del módulo legacy `views.py`.
"""
import os

from django.conf import settings
from openai import OpenAI


def generar_descripcion_vivienda(m2, hab, banos, ascensor):
    """Genera una descripción de anuncio inmobiliario con gpt-4o."""
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY no configurado en settings/.env')
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un experto en ventas inmobiliarias."},
            {"role": "user", "content": (
                f"Genera una descripción atractiva para un anuncio de vivienda con "
                f"{m2}m2, {hab} habitaciones, {banos} baños y "
                f"{'con' if ascensor else 'sin'} ascensor."
            )},
        ],
        stream=False,
    )
    return response.choices[0].message.content
