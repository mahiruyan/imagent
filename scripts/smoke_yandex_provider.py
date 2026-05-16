from __future__ import annotations

import argparse
import asyncio

from app.providers.factory import get_map_provider
from app.providers.yandex import YandexProviderError


async def smoke(query: str, city: str | None, limit: int) -> None:
    provider = get_map_provider("yandex")
    try:
        candidates = await provider.search_organizations(query=query, city=city, limit=limit)
    except YandexProviderError as exc:
        print(f"Yandex smoke test failed: {exc}")
        raise SystemExit(1) from exc
    print(f"provider={provider.provider_name} count={len(candidates)}")
    for candidate in candidates[:10]:
        print(
            " | ".join(
                value or "-"
                for value in [
                    candidate.name,
                    candidate.address,
                    candidate.phone,
                    candidate.website,
                    candidate.source_id,
                ]
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test the configured Yandex provider.")
    parser.add_argument("--query", default="CNC")
    parser.add_argument("--city", default="Izmir")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(smoke(args.query, args.city, args.limit))


if __name__ == "__main__":
    main()
