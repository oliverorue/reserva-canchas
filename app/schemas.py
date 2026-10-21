from datetime import date, time
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator


class CourtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ReservationCreate(BaseModel):
    court_id: int
    person_name: Annotated[str, StringConstraints(strip_whitespace=True)]
    date: date
    start_time: time
    end_time: time

    @field_validator("person_name")
    @classmethod
    def _validate_person_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre de la persona es obligatorio.")
        if len(value) > 100:
            raise ValueError("El nombre no puede superar los 100 caracteres.")
        return value


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    court_id: int
    person_name: str
    date: date
    start_time: time
    end_time: time
