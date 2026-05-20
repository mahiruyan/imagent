from __future__ import annotations

from app.core.config import settings
from app.providers.base import MapProvider
from app.providers.google import GoogleMapsProvider
from app.providers.yandex import YandexMapsProvider


def get_map_provider(provider_name: str | None = None) -> MapProvider:
    provider = provider_name or settings.map_provider
    if provider == "yandex":
        if not settings.yandex_backend_key:
            raise RuntimeError(
                "YANDEX_PLACES_API_KEY, YANDEX_MAPS_BACKEND_KEY, or YANDEX_MAPS_API_KEY is required for Yandex provider"
            )
        return YandexMapsProvider(api_key=settings.yandex_backend_key)
    if provider == "google":
        api_key = settings.google_maps_backend_key or settings.google_maps_api_key
        if not api_key:
            raise RuntimeError("GOOGLE_MAPS_BACKEND_KEY or GOOGLE_MAPS_API_KEY is required for Google provider")
        return GoogleMapsProvider(api_key=api_key)
    raise ValueError(f"Unsupported map provider: {provider}")
