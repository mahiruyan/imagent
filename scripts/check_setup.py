from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


async def check_database() -> CheckResult:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("select 1"))
        return CheckResult("database", True, "connection ok")
    except Exception as exc:
        return CheckResult("database", False, str(exc))


def check_env() -> list[CheckResult]:
    results = [
        CheckResult("DATABASE_URL", bool(settings.database_url), "set"),
        CheckResult("SECRET_KEY", bool(settings.secret_key), "set"),
        CheckResult("MAP_PROVIDER", settings.map_provider == "yandex", settings.map_provider),
        CheckResult(
            "YANDEX_PLACES_API_KEY",
            bool(settings.yandex_places_api_key),
            "set" if settings.yandex_places_api_key else "missing",
        ),
        CheckResult(
            "YANDEX_JS_API_KEY",
            bool(settings.yandex_js_api_key),
            "set" if settings.yandex_js_api_key else "missing",
        ),
    ]
    return results


async def main() -> None:
    results = check_env()
    results.append(await check_database())

    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")

    if not all(result.ok for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

