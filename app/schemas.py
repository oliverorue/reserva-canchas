from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field


class CourtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ReservationCreate(BaseModel):
    court_id: int
    person_name: str = Field(min_length=1, max_length=100)
    date: date
    start_time: time
    end_time: time


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    court_id: int
    person_name: str
    date: date
    start_time: time
    end_time: time
