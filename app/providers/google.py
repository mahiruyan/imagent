from __future__ import annotations

import httpx

from app.schemas.provider import CompanyCandidate, GeoBounds
from app.services.normalization import normalize_name, normalize_phone, normalize_website


class GoogleProviderError(RuntimeError):
    pass


class GoogleMapsProvider:
    provider_name = "google"
    places_base_url = "https://places.googleapis.com/v1"

    search_field_mask = ",".join(
        [
            "places.id",
        ]
    )
    details_field_mask = ",".join(
        [
            "id",
            "googleMapsUri",
            "displayName",
            "formattedAddress",
            "location",
            "nationalPhoneNumber",
            "internationalPhoneNumber",
            "websiteUri",
            "types",
            "rating",
            "userRatingCount",
            "businessStatus",
        ]
    )

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def search_organizations(
        self,
        query: str,
        city: str | None = None,
        bounds: GeoBounds | None = None,
        limit: int = 50,
    ) -> list[CompanyCandidate]:
        text_query = f"{query} {city}".strip() if city and city.lower() not in query.lower() else query
        payload: dict = {
            "textQuery": text_query,
            "languageCode": "tr",
            "regionCode": "TR",
            "pageSize": min(limit, 20),
        }
        if bounds:
            payload["locationBias"] = {
                "rectangle": {
                    "low": {"latitude": bounds.south, "longitude": bounds.west},
                    "high": {"latitude": bounds.north, "longitude": bounds.east},
                }
            }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.places_base_url}/places:searchText",
                json=payload,
                headers=self._headers(self.search_field_mask),
            )
            payload = self._json_or_raise(response, "Google Places Text Search")

        return [self._search_hit_to_candidate(place, city=city) for place in payload.get("places", [])]

    async def get_organization_details(self, provider_entity_id: str) -> CompanyCandidate:
        async with httpx.AsyncClient(timeout=30) as client:
            place = await self._fetch_place_details(client, provider_entity_id)
        return self._place_to_candidate(place, city=None)

    async def _fetch_place_details(self, client: httpx.AsyncClient, place_id: str) -> dict:
        response = await client.get(
            f"{self.places_base_url}/places/{place_id}",
            headers=self._headers(self.details_field_mask),
        )
        return self._json_or_raise(response, "Google Places Details")

    def _headers(self, field_mask: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }

    def _json_or_raise(self, response: httpx.Response, operation: str) -> dict:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            body = exc.response.text[:300]
            raise GoogleProviderError(
                f"{operation} failed with status={status_code}: {body}"
            ) from exc
        return response.json()

    def _place_to_candidate(self, place: dict, city: str | None = None) -> CompanyCandidate:
        display_name = place.get("displayName") or {}
        location = place.get("location") or {}
        name = display_name.get("text") or "Unknown organization"
        phone = place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber")
        website = place.get("websiteUri")

        return CompanyCandidate(
            source_provider="google",
            source_id=place.get("id"),
            source_url=place.get("googleMapsUri"),
            name=name,
            normalized_name=normalize_name(name),
            address=place.get("formattedAddress"),
            city=city,
            lat=location.get("latitude"),
            lng=location.get("longitude"),
            phone=phone,
            normalized_phone=normalize_phone(phone),
            website=normalize_website(website) if website else None,
            categories=place.get("types") or [],
            rating=place.get("rating"),
            review_count=place.get("userRatingCount"),
            needs_details=False,
            raw_payload=place,
        )

    def _search_hit_to_candidate(self, place: dict, city: str | None = None) -> CompanyCandidate:
        place_id = place.get("id")
        return CompanyCandidate(
            source_provider="google",
            source_id=place_id,
            name=place_id or "Unknown Google place",
            normalized_name=normalize_name(place_id or ""),
            city=city,
            needs_details=True,
            raw_payload=place,
        )
