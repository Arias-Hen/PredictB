from fpdf import FPDF
import os
from django.conf import settings
from django.utils import timezone
def generar_pdf(vivienda, imagenes):

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    logo_path = os.path.join(
    settings.BASE_DIR,
    'staticfiles',
    'images',
    'logo.jpeg'
    )
    if os.path.isfile(logo_path):
        pdf.image(logo_path, x=10, y=10, w=40)
    
    pdf.ln(30)

    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, "Reporte de Vivienda", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Resumen", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", size=10)
    columnas = ["Característica", "Valor"]
    datos = [
        ["Metros Cuadrados", str(vivienda.metros_cuadrados)],
        ["Habitaciones", str(vivienda.habitaciones)],
        ["Baños", str(vivienda.banos)],
        ["Ascensor", "Sí" if vivienda.ascensor else "No"]
    ]

    col_width = 90
    pdf.set_fill_color(200, 200, 200)
    for col in columnas:
        pdf.cell(col_width, 10, col, border=1, align='C', fill=True)
    pdf.ln()

    for row in datos:
        for item in row:
            pdf.cell(col_width, 10, item, border=1, align='C')
        pdf.ln()

    pdf.ln(10)
    pdf.multi_cell(0, 10, vivienda.descripcion)

    for img in imagenes:
        if os.path.exists(img):
            pdf.add_page()
            pdf.image(img, x=10, y=30, w=180)

    # ⬅️ Este path se usará para devolver al frontend
    output_path = os.path.join(settings.MEDIA_ROOT, 'reportes', f'reporte_vivienda_{vivienda.id}.pdf')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)

    return f"{settings.MEDIA_URL}reportes/reporte_vivienda_{vivienda.id}.pdf"  # Ruta relativa para el navegador
def _txt(s):
    """fpdf clásico usa latin-1; evita errores con caracteres fuera de ese set."""
    return str(s).encode('latin-1', 'replace').decode('latin-1')


def generar_informe_pdf(valoracion, tipo, imagenes, usuario):
    """Genera el PDF de un informe/dossier a partir de una valoración.

    Plantilla provisional (mientras llega la IA) con el formato de generarinf.html:
    Portada + Descripción del piso + Valoración. El 'dossier' añade el Perfil del
    comprador y todas las imágenes; el 'informe' es la versión resumida.
    Devuelve la ruta relativa (/media/...) del PDF.
    """
    es_dossier = tipo == 'dossier'
    titulo = 'DOSSIER INMOBILIARIO' if es_dossier else 'INFORME DE VALORACIÓN'

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    logo_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'images', 'logo.jpeg')
    if os.path.isfile(logo_path):
        pdf.image(logo_path, x=10, y=8, w=35)
    pdf.ln(28)

    # --- Portada ---
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 12, _txt(titulo), ln=True, align='C')
    pdf.ln(2)
    pdf.set_draw_color(0, 1, 160)
    pdf.set_line_width(0.6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    ubicacion = ', '.join([p for p in [valoracion.calle, valoracion.barrio,
                                       valoracion.distrito, valoracion.ciudad] if p])
    honorarios = round((valoracion.precio_esperado or 0) * 0.05, 2)

    def fila(label, value):
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(55, 8, _txt(label), border=0)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 8, _txt(value if value not in (None, '') else '-'))

    pdf.set_font('Arial', 'B', 13)
    pdf.cell(0, 9, '1. Portada', ln=True)
    fila('Inmobiliaria:', getattr(usuario, 'empresa', '') or '-')
    fila('Agente:', getattr(usuario, 'nombre', '') or getattr(usuario, 'usuario', ''))
    fila('Finca valorada en:', ubicacion)
    fila('Fecha de emisión:', timezone.now().strftime('%d/%m/%Y'))
    fila('Honorarios (5%):', f"{honorarios:,.2f} EUR")
    pdf.ln(3)

    # --- Descripción del piso ---
    pdf.set_font('Arial', 'B', 13)
    pdf.cell(0, 9, '2. Descripción del inmueble', ln=True)
    fila('Tipo de vivienda:', valoracion.tipo_vivienda)
    fila('Superficie:', f"{valoracion.metros_cuadrados} m2")
    fila('Distribución:', f"{valoracion.num_habitaciones} hab. / {valoracion.num_banos} baños")
    fila('Planta:', valoracion.planta)
    extras = ', '.join([e for e, ok in [('Terraza', valoracion.terraza),
                                        ('Balcón', valoracion.balcon),
                                        ('Ascensor', valoracion.ascensor)] if ok]) or 'Ninguno'
    fila('Extras:', extras)
    fila('Estado:', valoracion.estado_inmueble)
    pdf.ln(3)

    # --- Valoración (precios) ---
    pdf.set_font('Arial', 'B', 13)
    pdf.cell(0, 9, '3. Valoración estimada', ln=True)
    pdf.set_font('Arial', '', 10)
    precios = [
        ('Precio mínimo', valoracion.precio_minimo),
        ('Precio esperado', valoracion.precio_esperado),
        ('Precio máximo', valoracion.precio_maximo),
    ]
    if getattr(valoracion, 'correccion_manual', False) and valoracion.precio_corregido:
        precios.append(('Valor corregido', valoracion.precio_corregido))
    pdf.set_fill_color(230, 232, 245)
    for label, val in precios:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(95, 9, _txt(label), border=1, fill=True)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 9, _txt(f"{(val or 0):,.2f} EUR"), border=1, ln=True)
    pdf.ln(3)

    # --- Solo dossier: perfil del comprador ---
    if es_dossier:
        pdf.set_font('Arial', 'B', 13)
        pdf.cell(0, 9, '4. Perfil del comprador potencial', ln=True)
        fila('Edad media:', '35-50 años')
        fila('Nivel de ingresos:', 'Medio-alto')
        fila('Tipo de familia:', 'Familias y profesionales')

    # --- Imágenes (en ambos si se subieron; el dossier las prioriza) ---
    for img in (imagenes or []):
        if os.path.exists(img):
            pdf.add_page()
            pdf.image(img, x=10, y=25, w=185)

    # Devuelve (nombre, bytes) en vez de escribir a disco: el endpoint lo guarda
    # una sola vez vía el FileField (evita el doble archivo).
    nombre = f"{tipo}_valoracion_{valoracion.idv}_{int(timezone.now().timestamp())}.pdf"
    salida = pdf.output(dest='S')              # fpdf 1.7.x: str latin-1
    pdf_bytes = salida.encode('latin-1') if isinstance(salida, str) else bytes(salida)
    return nombre, pdf_bytes
