# Reserva de Canchas

Aplicación web fullstack para que un club administre las reservas de sus **3 canchas**, evitando reservas duplicadas (el problema que hoy se gestiona por WhatsApp).

## Stack

- **Backend:** Python 3 + FastAPI + SQLAlchemy 2.0 + Pydantic v2
- **Base de datos:** PostgreSQL (producción/Docker) o SQLite (desarrollo local)
- **Frontend:** server-rendered con Jinja2 + CSS propio + JavaScript mínimo (sin build step)
- **Tests:** pytest + httpx `TestClient`

## Funcionalidades

- Dashboard con las 3 canchas y las reservas del día.
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

Cubren superposición (incluido el solapado 10–11:30 vs 11–12), reservas consecutivas válidas, fecha pasada, duración fuera de rango (muy corta y muy larga), fin <= inicio, límites de 1 y 2 horas exactas, y cancelación.

## Estructura

```
app/
  config.py      # settings (DATABASE_URL)
  database.py    # engine + session
  models.py      # Court, Reservation
  schemas.py     # Pydantic schemas
  services.py    # reglas de negocio
  main.py        # app FastAPI + rutas + seed
templates/       # base, dashboard, courts, reservations
static/          # styles.css, app.js
tests/           # conftest + tests
```

## Uso de IA

*(Borrador — personalizar antes de entregar.)*

- **Herramienta:** Kilo (agente de IA basado en Claude).
- **Para qué se usó:** comprender el enunciado, diseñar el plan, generar el esqueleto del código (FastAPI + SQLAlchemy + Jinja2), escribir los tests, el `Dockerfile`/`docker-compose.yml` y un borrador de este README.
- **Qué se aceptó:** la estructura general, el modelo de datos, la lógica de las reglas de negocio y los tests.
- **Qué se modificó:** ajustes menores de nombres, mensajes y organización para mantenerlo simple y legible.
- **Qué se descartó:** propuestas innecesarias para el alcance del challenge (migraciones con Alembic, frontend SPA con build, manejo de zonas horarias).

## Problemas encontrados y alcance

- **Superposición con reservas consecutivas:** hubo que definir con precisión la condición de solape (`inicio_nueva < fin_existente` y `fin_nueva > inicio_existente`) para que 10–11 y 11–12 se consideren válidas.
- **Instalación de Docker/PostgreSQL:** Docker no estaba instalado inicialmente y su instalación requirió `sudo` y agregar el usuario al grupo `docker`. El flujo se validó primero con SQLite (desarrollo local) y luego contra PostgreSQL vía `docker compose up --build`, confirmando que el mismo código funciona en ambos motores.
- **Zona horaria:** las fechas/horas se manejan en hora local del servidor (sin timezone). Es suficiente para el challenge, pero es una limitación conocida si la app se desplegara multi-zona.
- **Alcance:** las 4 funcionalidades y las 4 reglas están completas. Quedan fuera (posibles mejoras): Alembic para migraciones, autenticación de usuarios, edición de reservas, notificaciones y manejo de timezones.
