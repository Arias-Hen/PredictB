import json

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
