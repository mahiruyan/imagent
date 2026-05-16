from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.query_catalog import QueryCatalog


QUERY_ROWS = [
    {
        "city": "Izmir",
        "district": "Cigli",
        "osb": "Ataturk OSB",
        "category": "cnc",
        "keyword": "CNC isleme",
        "query_text": "Ataturk OSB CNC isleme",
        "language": "tr",
        "priority": 10,
    },
    {
        "city": "Izmir",
        "district": "Kemalpasa",
        "osb": "Kemalpasa OSB",
        "category": "cnc",
        "keyword": "CNC torna",
        "query_text": "Kemalpasa OSB CNC torna",
        "language": "tr",
        "priority": 20,
    },
    {
        "city": "Izmir",
        "district": "Cigli",
        "osb": None,
        "category": "sheet_laser",
        "keyword": "lazer kesim",
        "query_text": "Cigli lazer kesim sac metal",
        "language": "tr",
        "priority": 30,
    },
    {
        "city": "Kocaeli",
        "district": "Gebze",
        "osb": "GEPOSB",
        "category": "plastic_injection",
        "keyword": "plastik enjeksiyon",
        "query_text": "GEPOSB plastik enjeksiyon",
        "language": "tr",
        "priority": 40,
    },
    {
        "city": "Kocaeli",
        "district": "Gebze",
        "osb": "Guzeller OSB",
        "category": "plastic_injection",
        "keyword": "plastic injection",
        "query_text": "Guzeller OSB plastic injection",
        "language": "en",
        "priority": 50,
    },
    {
        "city": "Bursa",
        "district": "Nilufer",
        "osb": "NOSAB",
        "category": "cnc",
        "keyword": "CNC machining",
        "query_text": "NOSAB CNC machining",
        "language": "en",
        "priority": 60,
    },
    {
        "city": "Istanbul",
        "district": "Tuzla",
        "osb": "Deri OSB",
        "category": "sheet_laser",
        "keyword": "sheet metal fabrication",
        "query_text": "Tuzla sheet metal fabrication",
        "language": "en",
        "priority": 70,
    },
    {
        "city": "Ankara",
        "district": "Yenimahalle",
        "osb": "OSTIM",
        "category": "3d_printing",
        "keyword": "3D baski",
        "query_text": "OSTIM 3D baski prototip",
        "language": "tr",
        "priority": 80,
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        inserted = 0
        for payload in QUERY_ROWS:
            existing = await session.scalar(
                select(QueryCatalog).where(QueryCatalog.query_text == payload["query_text"])
            )
            if existing:
                continue
            session.add(QueryCatalog(**payload))
            inserted += 1
        await session.commit()
    print(f"Seeded query catalog rows: {inserted}")


if __name__ == "__main__":
    asyncio.run(seed())

