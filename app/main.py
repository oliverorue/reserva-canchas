from contextlib import asynccontextmanager
from datetime import date, datetime, time
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.database import Base, SessionLocal, engine, get_db
from app.schemas import ReservationCreate, ReservationOut
from app.services import create_reservation

COURT_NAMES = ["Cancha 1", "Cancha 2", "Cancha 3"]


def seed_courts(db: Session) -> None:
    existing = {name for name in db.scalars(select(models.Court.name))}
    for name in COURT_NAMES:
        if name not in existing:
            db.add(models.Court(name=name))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_courts(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Reserva de Canchas", lifespan=lifespan)
BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida. Usar YYYY-MM-DD.")


def _parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Hora inválida. Usar HH:MM.")


DAY_START_MINUTES = 8 * 60
DAY_END_MINUTES = 22 * 60
SLOT_MINUTES = 30


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def build_day_schedule(courts: list[models.Court], reservations: list[models.Reservation]) -> dict:
    n_slots = (DAY_END_MINUTES - DAY_START_MINUTES) // SLOT_MINUTES
    slot_labels = [
        f"{(DAY_START_MINUTES + i * SLOT_MINUTES) // 60:02d}:{(DAY_START_MINUTES + i * SLOT_MINUTES) % 60:02d}"
        for i in range(n_slots)
    ]
    by_court = {c.id: [r for r in reservations if r.court_id == c.id] for c in courts}

    grid: dict[int, list[dict]] = {}
    for court in courts:
        cells: list[dict] = [{"kind": "free"} for _ in range(n_slots)]
        for r in by_court[court.id]:
            start_min = _to_minutes(r.start_time)
            end_min = _to_minutes(r.end_time)
            if end_min <= DAY_START_MINUTES or start_min >= DAY_END_MINUTES:
                continue
            start_slot = max(0, (start_min - DAY_START_MINUTES) // SLOT_MINUTES)
            end_slot = min(n_slots, ((end_min - DAY_START_MINUTES - 1) // SLOT_MINUTES) + 1)
            if end_slot <= start_slot:
                end_slot = start_slot + 1
            cells[start_slot] = {"kind": "start", "reservation": r, "span": end_slot - start_slot}
            for i in range(start_slot + 1, end_slot):
                cells[i] = {"kind": "covered"}
        grid[court.id] = cells

    return {"n_slots": n_slots, "slot_labels": slot_labels, "grid": grid}


@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    courts = list(db.scalars(select(models.Court).order_by(models.Court.id)))
    reservations = list(
        db.scalars(
            select(models.Reservation)
            .where(models.Reservation.date == today)
            .order_by(models.Reservation.start_time)
        )
    )
    by_court = {c.id: [r for r in reservations if r.court_id == c.id] for c in courts}
    schedule = build_day_schedule(courts, reservations)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "courts": courts,
            "by_court": by_court,
            "today": today,
            "reservations_today": len(reservations),
            "schedule": schedule,
            "error": request.query_params.get("error"),
            "success": request.query_params.get("success"),
        },
    )


@app.get("/courts")
def list_courts(request: Request, db: Session = Depends(get_db)):
    courts = list(db.scalars(select(models.Court).order_by(models.Court.id)))
    return templates.TemplateResponse(
        request, "courts.html", {"courts": courts}
    )


@app.get("/courts/{court_id}/reservations")
def court_reservations(
    request: Request,
    court_id: int,
    db: Session = Depends(get_db),
    date: str | None = None,
):
    court = db.get(models.Court, court_id)
    if court is None:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")

    day = _parse_date(date) if date else date.today()
    reservations = list(
        db.scalars(
            select(models.Reservation)
            .where(models.Reservation.court_id == court_id, models.Reservation.date == day)
            .order_by(models.Reservation.start_time)
        )
    )
    return templates.TemplateResponse(
        request,
        "reservations.html",
        {
            "court": court,
            "day": day,
            "reservations": reservations,
            "error": request.query_params.get("error"),
            "success": request.query_params.get("success"),
        },
    )


@app.post("/reservations")
def create(
    court_id: int = Form(...),
    person_name: str = Form(...),
    date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    db: Session = Depends(get_db),
):
    court = db.get(models.Court, court_id)
    if court is None:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")

    try:
        data = ReservationCreate(
            court_id=court_id,
            person_name=person_name.strip(),
            date=_parse_date(date),
            start_time=_parse_time(start_time),
            end_time=_parse_time(end_time),
        )
    except HTTPException as exc:
        return _redirect_back(court_id, date, error=exc.detail)

    result = create_reservation(db, data)
    if isinstance(result, list):
        return _redirect_back(court_id, date, error=" ".join(result))

    return _redirect_back(
        court_id, date, success=f"Reserva creada para {result.person_name}."
    )


@app.post("/reservations/{reservation_id}/cancel")
def cancel(
    reservation_id: int,
    court_id: int = Form(...),
    date: str = Form(...),
    db: Session = Depends(get_db),
):
    reservation = db.get(models.Reservation, reservation_id)
    if reservation is None:
        return _redirect_back(court_id, date, error="La reserva no existe.")

    db.delete(reservation)
    db.commit()
    return _redirect_back(court_id, date, success="Reserva cancelada.")


def _redirect_back(court_id: int, day: str, error: str | None = None, success: str | None = None):
    params = {}
    if day != "":
        params["date"] = day
    if error:
        params["error"] = error
    if success:
        params["success"] = success
    query = urlencode(params)
    url = f"/courts/{court_id}/reservations"
    if query:
        url += f"?{query}"
    return RedirectResponse(url, status_code=303)


@app.get("/api/reservations")
def api_reservations(
    court_id: int,
    date: str,
    db: Session = Depends(get_db),
) -> list[ReservationOut]:
    day = _parse_date(date)
    reservations = list(
        db.scalars(
            select(models.Reservation)
            .where(models.Reservation.court_id == court_id, models.Reservation.date == day)
            .order_by(models.Reservation.start_time)
        )
    )
    return [ReservationOut.model_validate(r) for r in reservations]
