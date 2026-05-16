from __future__ import annotations

from app.core.config import settings
from app.providers.base import MapProvider
from app.providers.yandex import YandexMapsProvider


def get_map_provider(provider_name: str | None = None) -> MapProvider:
    provider = provider_name or settings.map_provider
    if provider == "yandex":
        if not settings.yandex_places_api_key:
            raise RuntimeError("YANDEX_PLACES_API_KEY is required for Yandex provider")
        return YandexMapsProvider(api_key=settings.yandex_places_api_key)
    raise ValueError(f"Unsupported map provider: {provider}")

