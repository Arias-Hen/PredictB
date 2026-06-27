# PredictB — Backend (`interfaz_pr`)

Backend **Django 5.1 API-only** de **PredictBuild** (Ignite Labs), una herramienta de
valoración inmobiliaria para el mercado español. Los usuarios introducen las
características de una vivienda (`ciudad`/`distrito`/`barrio`/`calle`, m², habitaciones,
planta, terraza/ascensor, etc.), obtienen un rango de precios (mínimo/esperado/máximo),
los guardan como **valoraciones**, los exportan a Excel y generan **informes/dossiers** en
PDF con descripción escrita por IA.

El **frontend es React** y vive en un proyecto aparte; este repositorio expone únicamente
dos APIs REST:

- `/api/…` — API pública (usuarios finales).
- `/api/admin/…` — API del panel de administración (requiere `is_staff=True`).

> El proyecto es **API-only**: `interfaz_pr/urls.py` solo monta `/api/` y `/api/admin/`.
> Los templates Django bajo `home/templates/` son **legacy** (referencia visual del flujo
> antiguo) y ya no están enrutados.

---

## Requisitos

- **Python 3.12**
- SQLite (desarrollo, por defecto) o **PostgreSQL / Neon** (producción)
- Una cuenta de OpenAI y un SMTP (Gmail) si vas a probar generación de descripciones IA y
  envío de correos. Son opcionales para el resto de la API.

---

## Instalación (desarrollo, SQLite)

```powershell
# 1. Entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate           # Linux/Mac

# 2. Dependencias
pip install -r requirements.txt
```

> ⚠️ `requirements.txt` está codificado en **UTF-16 LE**. Ábrelo/edítalo como UTF-16.
> Si lo regeneras (`pip freeze`), guárdalo en UTF-8 o vuelve a convertirlo.

```powershell
# 3. Variables de entorno
copy .env.example .env                # Windows
# cp .env.example .env                # Linux/Mac
```

Edita `.env`. Para desarrollo rápido basta con:

```ini
SECRET_KEY=pon-algo-aleatorio
DEBUG=True
USE_SQLITE=True
```

```powershell
# 4. Base de datos + datos semilla
python manage.py migrate
python manage.py import_locations     # carga ciudades/distritos/barrios/calles (ver abajo)
python manage.py seed_users           # crea un admin y un usuario de prueba (opcional)

# 5. Arrancar
python manage.py runserver            # http://127.0.0.1:8000/
```

**Importante:** en una BD nueva las tablas de ubicaciones están vacías. Si no ejecutas
`import_locations`, el endpoint `/api/locations/` y todos los desplegables en cascada
(ciudad → distrito → barrio → calle) devolverán listas vacías o `500 no such table:
ciudades`.

### Usuarios de prueba (`seed_users`)

Comando idempotente (resetea contraseñas en cada ejecución):

| Rol     | usuario     | password    |
|---------|-------------|-------------|
| ADMIN   | `Ignite123` | `Ignite123` |
| usuario | `will123`   | `password`  |

```powershell
python manage.py createsuperuser      # alternativa: pide `usuario` (no `username`)
```

---

## Base de datos: SQLite vs PostgreSQL/Neon

El motor se elige con `USE_SQLITE` en `.env`:

- `USE_SQLITE=True` → `db.sqlite3` local (desarrollo).
- `USE_SQLITE=False` → PostgreSQL con las credenciales `DB_*` (producción/Neon).

Los **tests** siempre usan SQLite en memoria (`settings.py` detecta `'test'` en `sys.argv`),
así que **no tocan Neon**.

### Migraciones contra Neon (primera vez)

Neon ya tiene las tablas creadas manualmente. La primera vez, **falsea** las migraciones que
recrearían tablas existentes:

```powershell
python manage.py migrate home --fake 0002_user_groups_permissions_and_models
```

Después, cualquier cambio de campos hay que aplicarlo a Neon manualmente **y** falsearlo en
Django, o generar un ALTER real con cuidado.

---

## Datos de ubicaciones (`import_locations`)

Carga las tablas `Ciudad/Distrito/Barrio/Calle` (db_tables `ciudades`/`distritos`/`barrios`/
`calles`) desde los CSV (`ISO-8859-1`) en `home/csv/`:

- `distritos.csv` → Ciudad + Distrito (con `precio_m2_distrito`)
- `tb_todo_precio_m2.csv` → Barrio + Calle (con `precio_m2_barrio`/`precio_m2_calle`)

Es idempotente (`get_or_create`). La API pública `/api/locations/` lee de estas tablas; la API
admin `/api/admin/locations/` lee de la tabla `ventas` (solo ciudades ya valoradas).

---

## Autenticación (para el frontend React)

Toda la API usa **SessionAuthentication** (cookie). Desde React:

1. Llama una vez a `GET /api/auth/csrf/` al arrancar → fija la cookie `csrftoken`.
2. Envía `credentials: 'include'` en cada petición.
3. En escrituras (POST/PUT/PATCH/DELETE) manda el header `X-CSRFToken` con el valor de esa
   cookie.

CORS viene preconfigurado para `localhost:5173` (Vite) y `localhost:3000` (CRA/Next) con
`CORS_ALLOW_CREDENTIALS = True`.

---

## Endpoints

### Pública — `/api/…`

| Endpoint | Método | Notas |
|---|---|---|
| `/api/auth/csrf/` | GET | Fija la cookie `csrftoken` |
| `/api/auth/login/` | POST | `{usuario, password}` |
| `/api/auth/logout/` | POST | |
| `/api/auth/me/` | GET | Usuario actual |
| `/api/auth/register/` | POST | Valida contraseña y auto-loguea (201) |
| `/api/locations/?level=…` | GET | `ciudades/distritos/barrios/calles` con parámetro padre |
| `/api/valoraciones/` | CRUD | Solo las del usuario logueado |
| `/api/valoraciones/radar/` | POST | Datos de radar normalizados |
| `/api/valoraciones/export-excel/` | POST | `{ids:[…]}` → `.xlsx` con las filas seleccionadas |
| `/api/viviendas/` | POST | Crea vivienda + descripción IA + PDF + `Informe`. Acepta `valoracion` (id) como fuente de verdad |
| `/api/viviendas/<id>/enviar-email/` | POST | Genera el PDF y lo envía por email al usuario |
| `/api/informes/` | GET | Lista/lectura de los informes del usuario |
| `/api/informes/generar/` | POST | `{valoracion, tipo, imagenes[]}` → genera PDF informe/dossier y lo devuelve (`pdf_url`) |
| `/api/contacto/` | POST | Formulario de contacto por email |

### Admin — `/api/admin/…` (requiere `is_staff=True`)

| Endpoint | Método | Notas |
|---|---|---|
| `/api/admin/auth/{login,logout,me}/` | | `login` rechaza no-staff con 403 |
| `/api/admin/stats/` | GET | Métricas del dashboard + top-10 ciudades |
| `/api/admin/locations/?level=…` | GET | Desplegables desde la tabla `ventas` |
| `/api/admin/users/` | CRUD | + `set-password/`, `toggle-active/` |
| `/api/admin/valoraciones/` | CRUD | Filtros varios + `export-excel/` (`{ids:[…]}` → xlsx) |
| `/api/admin/informes/` | CRUD | |
| `/api/admin/viviendas/` `imagenes/` | CRUD | |

Los listados de valoraciones e informes incluyen un objeto anidado `usuario`
(`id`, `usuario`, `nombre`, `email`, `empresa`) para identificar al autor.

---

## Estructura del proyecto

```
PredictB/
├── interfaz_pr/            # Paquete del proyecto Django
│   ├── settings.py         # Config (todo desde .env; toggle USE_SQLITE)
│   ├── urls.py             # API-only: monta /api/ y /api/admin/
│   └── wsgi.py
├── home/                   # App única
│   ├── models.py           # Users, Valoracion(ventas), Informe, Vivienda, Ciudad/Distrito/Barrio/Calle, PredictionModel
│   ├── views_public.py     # API pública  + urls_public.py
│   ├── views_admin.py      # API admin     + urls_admin.py
│   ├── serializers.py      # Serializers de ambas APIs
│   ├── views.py            # Vistas legacy (templates, no enrutadas)
│   ├── backends.py         # CustomUserBackend (login por `usuario`)
│   ├── utils.py            # generar_pdf / generar_informe_pdf (fpdf)
│   ├── locations.py        # Lectura de ubicaciones para la API pública
│   ├── csv/                # CSVs de ubicaciones y precios (ISO-8859-1)
│   ├── management/commands/  # import_locations, seed_users
│   ├── migrations/
│   └── templates/          # Templates legacy (referencia)
├── mediafiles/             # MEDIA_ROOT (PDFs, imágenes subidas)
├── staticfiles/            # Assets fuente (logo, etc.)
├── static/                 # STATIC_ROOT (collectstatic)
├── requirements.txt        # ⚠️ UTF-16 LE
├── .env.example            # Plantilla de variables de entorno
├── app.yaml                # Despliegue App Engine
├── vercel.json             # Despliegue Vercel
└── manage.py
```

### Modelo de usuario y datos (claves)

- `AUTH_USER_MODEL = 'home.Users'`, tabla `usuarios`, PK `uniqueid`, `USERNAME_FIELD = 'usuario'`.
- `Valoracion` → tabla `ventas`, PK `idv`, FK `iduser` (a `Users`, `db_constraint=False`).
- `Informe` → tabla `informes`, FK `usuario` y FK opcional `valoracion` (origen del PDF), campo `tipo` (`informe`/`dossier`).
- `PredictionModel.get_radar_data` abre su propia conexión `psycopg2` a
  `data.inv_agrupacion_viviendas_madrid` (agregados precalculados, fuera de Django).

---

## Servicios externos

- **OpenAI** (`gpt-4o`): descripción de viviendas. Requiere `OPENAI_API_KEY` en `.env`.
- **SMTP (Gmail)**: contacto y envío de PDFs. Variables `EMAIL_*` / `DEFAULT_FROM_EMAIL`.
- **fpdf** (1.7.x): generación de PDFs (`home/utils.py`).
- **pandas + openpyxl**: exportación a Excel.

---

## Tests

```powershell
python manage.py test home          # SQLite en memoria, no toca Neon
```

Son `TestCase` de Django + `APIClient` de DRF. Al correr sobre SQLite, cualquier función
específica de PostgreSQL no se ejercita.

---

## Comandos útiles

```powershell
python manage.py migrate                  # aplica migraciones
python manage.py import_locations         # siembra ubicaciones (necesario en BD nueva)
python manage.py seed_users               # usuarios de prueba (admin + usuario)
python manage.py createsuperuser          # pide `usuario`, no `username`
python manage.py collectstatic --noinput  # recopila en ./static
python manage.py runserver                # http://127.0.0.1:8000/
python manage.py check                    # chequeo del sistema
```

---

## Despliegue

- **App Engine** (`app.yaml`): `python311`, gunicorn.
- **Vercel** (`vercel.json`): `python3.12.2`. ⚠️ El filesystem es **efímero**: los PDFs
  escritos en `MEDIA_ROOT` y las imágenes subidas (`ImageField`) **no persisten**. Antes de
  desplegar ahí, migra el almacenamiento a S3/GCS (`boto3` ya está en `requirements.txt`).
```
