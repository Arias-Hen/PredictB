import json
from fpdf import FPDF
import os
from django.conf import settings
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
def load_data():
    """Cargar datos desde un archivo JSON."""
    try:
        with open('datos.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_data(data):
    """Guardar datos en un archivo JSON."""
    with open('datos.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
