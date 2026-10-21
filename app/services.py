from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import CLUB_CLOSE_MINUTES, CLUB_OPEN_MINUTES
from app.models import Reservation
from app.schemas import ReservationCreate

MIN_DURATION_MINUTES = 60
MAX_DURATION_MINUTES = 120


def duration_minutes(start_time: time, end_time: time) -> int:
    delta = datetime.combine(date.min, end_time) - datetime.combine(date.min, start_time)
    return int(delta.total_seconds() // 60)


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _overlaps(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    return start_a < end_b and end_a > start_b


def validate_rules(data: ReservationCreate, existing: list[Reservation]) -> list[str]:
    """Return a list of error messages. Empty list means the reservation is valid."""
    errors: list[str] = []

    if data.end_time <= data.start_time:
        errors.append("La hora de fin debe ser posterior a la hora de inicio.")
        return errors

    duration = duration_minutes(data.start_time, data.end_time)
    if duration < MIN_DURATION_MINUTES:
        errors.append("La reserva debe durar al menos 60 minutos (1 hora).")
    elif duration > MAX_DURATION_MINUTES:
        errors.append("La reserva no puede durar más de 120 minutos (2 horas).")

    if (
        _to_minutes(data.start_time) < CLUB_OPEN_MINUTES
        or _to_minutes(data.end_time) > CLUB_CLOSE_MINUTES
    ):
        errors.append("El club está cerrado en ese horario (abierto de 08:00 a 22:00).")

    start_dt = datetime.combine(data.date, data.start_time)
    if start_dt <= datetime.now():
        errors.append("No se puede reservar en una fecha/hora pasada.")

    for res in existing:
        if _overlaps(
            data.start_time,
            data.end_time,
            res.start_time,
            res.end_time,
        ):
            errors.append(
                f"La cancha ya está reservada de {res.start_time.strftime('%H:%M')} "
                f"a {res.end_time.strftime('%H:%M')} ese día."
            )
            break

    return errors


def find_overlapping(db: Session, court_id: int, day: date) -> list[Reservation]:
    stmt = (
        select(Reservation)
        .where(Reservation.court_id == court_id, Reservation.date == day)
        .order_by(Reservation.start_time)
    )
    return list(db.scalars(stmt).all())


def create_reservation(db: Session, data: ReservationCreate) -> Reservation | list[str]:
    existing = find_overlapping(db, data.court_id, data.date)
    errors = validate_rules(data, existing)
    if errors:
        return errors

    reservation = Reservation(
        court_id=data.court_id,
        person_name=data.person_name,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation
