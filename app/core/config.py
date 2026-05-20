from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")
    secret_key: str = Field(alias="SECRET_KEY")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", alias="ENVIRONMENT"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    map_provider: Literal["yandex", "google"] = Field(default="yandex", alias="MAP_PROVIDER")
    yandex_js_api_key: str | None = Field(default=None, alias="YANDEX_JS_API_KEY")
    yandex_places_api_key: str | None = Field(default=None, alias="YANDEX_PLACES_API_KEY")
    yandex_maps_api_key: str | None = Field(default=None, alias="YANDEX_MAPS_API_KEY")
    yandex_maps_backend_key: str | None = Field(default=None, alias="YANDEX_MAPS_BACKEND_KEY")
    google_maps_api_key: str | None = Field(default=None, alias="GOOGLE_MAPS_API_KEY")
    google_maps_backend_key: str | None = Field(default=None, alias="GOOGLE_MAPS_BACKEND_KEY")
    export_template_path: str | None = Field(default=None, alias="EXPORT_TEMPLATE_PATH")
    frontend_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="FRONTEND_ORIGINS",
    )

    @property
    def frontend_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def yandex_backend_key(self) -> str | None:
        return self.yandex_places_api_key or self.yandex_maps_backend_key or self.yandex_maps_api_key

    @property
    def yandex_browser_key(self) -> str | None:
        return self.yandex_js_api_key or self.yandex_maps_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
