from datetime import date, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Reservation

TOMORROW = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
YESTERDAY = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")


def _count_reservations() -> int:
    session = SessionLocal()
    try:
        return len(session.scalars(select(Reservation)).all())
    finally:
        session.close()


def _get_csrf(client) -> str:
    client.get(f"/courts/1/reservations?date={TOMORROW}")
    return client.cookies.get("csrf_token")


def _post(client, court_id=1, name="Juan Pérez", day=TOMORROW, start="10:00", end="11:00"):
    token = _get_csrf(client)
    return client.post(
        "/reservations",
        data={
            "court_id": court_id,
            "person_name": name,
            "date": day,
            "start_time": start,
            "end_time": end,
            "csrf_token": token,
        },
        follow_redirects=False,
    )


def test_seed_creates_three_courts(client):
    resp = client.get("/courts")
    assert resp.status_code == 200
    for name in ["Cancha 1", "Cancha 2", "Cancha 3"]:
        assert name in resp.text


def test_create_valid_reservation(client):
    resp = _post(client)
    assert resp.status_code == 303
    assert "success=" in resp.headers["location"]
    assert _count_reservations() == 1


def test_overlap_rejected(client):
    assert _post(client, start="10:00", end="11:30").status_code == 303
    resp = _post(client, name="Ana", start="11:00", end="12:00")
    assert "error=" in resp.headers["location"]
    assert _count_reservations() == 1


def test_consecutive_reservations_valid(client):
    assert _post(client, start="10:00", end="11:00").status_code == 303
    resp = _post(client, name="Ana", start="11:00", end="12:00")
    assert "success=" in resp.headers["location"]
    assert _count_reservations() == 2


def test_past_date_rejected(client):
    resp = _post(client, day=YESTERDAY)
    assert "error=" in resp.headers["location"]
    assert _count_reservations() == 0


def test_duration_too_long_rejected(client):
    resp = _post(client, start="10:00", end="13:00")
    assert "error=" in resp.headers["location"]
    assert _count_reservations() == 0


def test_duration_too_short_rejected(client):
    resp = _post(client, start="10:00", end="10:30")
    assert "error=" in resp.headers["location"]
    assert _count_reservations() == 0


def test_end_before_start_rejected(client):
    resp = _post(client, start="12:00", end="11:00")
    assert "error=" in resp.headers["location"]
    assert _count_reservations() == 0


def test_club_closed_before_open_rejected(client):
    resp = _post(client, start="07:00", end="08:00")
    assert "error=" in resp.headers["location"]
    assert _count_reservations() == 0


def test_club_closed_after_close_rejected(client):
    resp = _post(client, start="21:30", end="22:30")
    assert "error=" in resp.headers["location"]
    assert _count_reservations() == 0


def test_empty_name_rejected(client):
    resp = _post(client, name="   ")
    assert "error=" in resp.headers["location"]
    assert _count_reservations() == 0


def test_csrf_required(client):
    resp = client.post(
        "/reservations",
        data={
            "court_id": 1,
            "person_name": "X",
            "date": TOMORROW,
            "start_time": "10:00",
            "end_time": "11:00",
            "csrf_token": "token-falso",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 403


def test_exact_one_hour_valid(client):
    resp = _post(client, start="10:00", end="11:00")
    assert "success=" in resp.headers["location"]


def test_exact_two_hours_valid(client):
    resp = _post(client, start="10:00", end="12:00")
    assert "success=" in resp.headers["location"]


def test_cancel_reservation(client):
    assert _post(client, start="10:00", end="11:00").status_code == 303
    session = SessionLocal()
    try:
        reservation_id = session.scalars(select(Reservation)).first().id
    finally:
        session.close()

    resp = client.post(
        f"/reservations/{reservation_id}/cancel",
        data={"court_id": 1, "date": TOMORROW, "csrf_token": _get_csrf(client)},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "success=" in resp.headers["location"]
    assert _count_reservations() == 0
