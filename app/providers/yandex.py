from __future__ import annotations

import httpx

from app.schemas.provider import CompanyCandidate, GeoBounds
from app.services.normalization import normalize_name, normalize_phone, normalize_website


class YandexProviderError(RuntimeError):
    pass


class YandexMapsProvider:
    provider_name = "yandex"
    base_url = "https://search-maps.yandex.ru/v1/"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def search_organizations(
        self,
        query: str,
        city: str | None = None,
        bounds: GeoBounds | None = None,
        limit: int = 50,
    ) -> list[CompanyCandidate]:
        text = f"{query} {city}".strip() if city and city.lower() not in query.lower() else query
        params: dict[str, str | int] = {
            "apikey": self.api_key,
            "text": text,
            "lang": "tr_TR",
            "type": "biz",
            "results": min(limit, 500),
        }
        if bounds:
            params["bbox"] = f"{bounds.west},{bounds.south}~{bounds.east},{bounds.north}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.base_url, params=params)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                body = exc.response.text[:300]
                raise YandexProviderError(
                    f"Yandex Maps API request failed with status={status_code}: {body}"
                ) from exc
            payload = response.json()

        return [self._feature_to_candidate(feature, city=city) for feature in payload.get("features", [])]

    async def get_organization_details(self, provider_entity_id: str) -> CompanyCandidate:
        raise NotImplementedError("Yandex details lookup will be added after confirming API shape")

    def _feature_to_candidate(self, feature: dict, city: str | None = None) -> CompanyCandidate:
        properties = feature.get("properties") or {}
        metadata = properties.get("CompanyMetaData") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or [None, None]
        lng, lat = coordinates[0], coordinates[1]

        phones = metadata.get("Phones") or []
        phone = None
        if phones:
            phone = phones[0].get("formatted") or phones[0].get("number")

        url = metadata.get("url")
        categories = [
            category.get("name")
            for category in metadata.get("Categories", [])
            if isinstance(category, dict) and category.get("name")
        ]
        address = metadata.get("address") or properties.get("description")
        name = metadata.get("name") or properties.get("name") or "Unknown organization"
        source_id = metadata.get("id") or feature.get("uri")

        return CompanyCandidate(
            source_provider="yandex",
            source_id=source_id,
            source_url=feature.get("uri"),
            name=name,
            normalized_name=normalize_name(name),
            address=address,
            city=city,
            lat=lat,
            lng=lng,
            phone=phone,
            normalized_phone=normalize_phone(phone),
            website=normalize_website(url) if url else None,
            categories=categories,
            raw_payload=feature,
        )
