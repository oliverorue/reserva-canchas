# Reserva de Canchas

Aplicación web fullstack para que un club administre las reservas de sus **3 canchas**, evitando reservas duplicadas (el problema que hoy se gestiona por WhatsApp).

## Stack

- **Backend:** Python 3 + FastAPI + SQLAlchemy 2.0 + Pydantic v2
- **Base de datos:** PostgreSQL (producción/Docker) o SQLite (desarrollo local)
- **Frontend:** server-rendered con Jinja2 + CSS propio + JavaScript mínimo (sin build step)
- **Tests:** pytest + httpx `TestClient`

## Funcionalidades

- Dashboard con las 3 canchas, contador de reservas del día y **agenda diaria** (grilla por horas).
- Listado de canchas.
- Reservas por cancha y por día, con selector de fecha.
- Crear reserva.
- Cancelar reserva.

## Reglas de negocio

Una reserva se rechaza con un mensaje claro si:

1. **Superposición:** misma cancha + mismo día y `inicio_nueva < fin_existente` **y** `fin_nueva > inicio_existente`. Las reservas consecutivas (p. ej. 10–11 y 11–12) son válidas.
2. **Fecha/hora pasada:** la hora de inicio ya pasó.
3. **Fin <= inicio:** la hora de fin no es posterior a la de inicio.
4. **Duración fuera de rango:** debe durar entre 60 y 120 minutos (1 a 2 horas inclusive).
5. **Club cerrado** *(opcional)*: no se admiten reservas fuera del horario de apertura (08:00 a 22:00).

## Cómo ejecutar

### Con Docker (PostgreSQL)

```bash
docker compose up --build
```

La app queda disponible en <http://localhost:8000>. La base de datos PostgreSQL se levanta en un contenedor `db` con healthcheck y volumen persistente.

### Sin Docker (SQLite)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Usa por defecto `DATABASE_URL=sqlite:///./reservas.db`. La app crea las tablas y siembra las 3 canchas automáticamente al arrancar.

### Configuración

Todo pasa por la variable de entorno `DATABASE_URL` (ver `.env.example`):

| Entorno        | Valor                                                     |
| -------------- | --------------------------------------------------------- |
| Local (SQLite) | `sqlite:///./reservas.db`                                 |
| Docker (PostgreSQL) | `postgresql+psycopg://usuario:pass@db:5432/reservas` |

## Tests

```bash
pytest
```

Cubren superposición (incluido el solapado 10–11:30 vs 11–12), reservas consecutivas válidas, fecha pasada, duración fuera de rango (muy corta y muy larga), fin <= inicio, club cerrado (antes de apertura y después del cierre), nombre vacío, límites de 1 y 2 horas exactas, y cancelación.

## Estructura

```
app/
  config.py      # settings (DATABASE_URL) + horario del club
  database.py    # engine + session
  models.py      # Court, Reservation
  schemas.py     # Pydantic schemas (validación de entrada)
  services.py    # reglas de negocio
  main.py        # app FastAPI + rutas + seed + CSRF
templates/       # base, dashboard, courts, reservations
static/          # styles.css, app.js
tests/           # conftest + tests
```

## Detalles técnicos

- **CSRF:** los formularios `POST` (crear/cancelar) llevan un token CSRF en cookie (doble envío) que se valida en el servidor.
- **Índice:** la tabla `reservations` tiene un índice compuesto `(court_id, date)` para acelerar la consulta de superposición.
- **Timezones:** las horas/fechas de negocio (`date`, `start_time`, `end_time`) se guardan en hora local; el `created_at` se guarda en UTC (`timestamp with time zone`).
- **Validación con Pydantic:** el nombre se limpia (`strip_whitespace`) y valida dentro del esquema, no en la ruta.

## Uso de IA

- **Herramientas:** Kilo (agente de IA, conectado a través de la API de DeepSeek) y Gemini (para sugerencias de mejora).
- **Para qué las usé:** comprender el enunciado y las reglas de negocio, diseñar la arquitectura, generar el código del backend (FastAPI + SQLAlchemy), el frontend (Jinja2 + CSS), los tests, el `Dockerfile`/`docker-compose.yml` y este README, además de corregir errores detectados durante las pruebas (por ejemplo, la zona horaria del contenedor).
- **Qué acepté sin cambios:** la mayor parte del código generado (modelos, servicios, rutas, templates y tests).
- **Qué modifiqué:** incorporé mejoras técnicas que consulté con Gemini — validación con Pydantic, protección CSRF, índice compuesto en la base de datos y `created_at` en UTC — y ajusté textos y mensajes.
- **Qué descarté:** propuestas que excedían el alcance del challenge (migraciones con Alembic, frontend SPA con build step, autenticación de usuarios).
- Declaro que comprendo el funcionamiento de cada parte del código y puedo explicarlo, haya sido escrita por una herramienta o no.

## Problemas encontrados y alcance

- **Superposición con reservas consecutivas:** hubo que definir con precisión la condición de solape (`inicio_nueva < fin_existente` y `fin_nueva > inicio_existente`) para que 10–11 y 11–12 se consideren válidas.
- **Instalación de Docker/PostgreSQL:** Docker no estaba instalado inicialmente y su instalación requirió `sudo` y agregar el usuario al grupo `docker`. El flujo se validó primero con SQLite (desarrollo local) y luego contra PostgreSQL vía `docker compose up --build`, confirmando que el mismo código funciona en ambos motores.
- **Zona horaria:** las horas/fechas de negocio se manejan en hora local del servidor (sin timezone), comparando contra `datetime.now()` local; en Docker se monta `/etc/localtime` del host para que el contenedor coincida con la hora local y la regla de "fechas pasadas" sea correcta. El `created_at` sí se guarda en UTC. Para un despliegue multi-zona real habría que migrar toda la lógica de negocio a datetimes con timezone.
- **Alcance:** las 4 funcionalidades y las 4 reglas obligatorias están completas. También se implementaron los tres aspectos opcionales: la grilla por horas del día, las pruebas automáticas de superposición y la regla de club cerrado (08:00–22:00). Quedan fuera (posibles mejoras): Alembic para migraciones, autenticación de usuarios, edición de reservas, notificaciones y manejo de timezones.
