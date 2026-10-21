from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./reservas.db"


settings = Settings()


# Horario de apertura/cierre del club (regla opcional de "club cerrado").
CLUB_OPEN_MINUTES = 8 * 60   # 08:00
CLUB_CLOSE_MINUTES = 22 * 60  # 22:00
