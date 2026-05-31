"""Standalone index creation: ``python -m app.scripts.create_indexes``.

Creates every index defined in ``app/data/indexes.py`` against the configured
database. Idempotent -- safe to run repeatedly (e.g. in a deploy step). The
FastAPI lifespan also ensures these on startup; this script exists for
out-of-band provisioning and CI.
"""

import asyncio

from app.data.indexes import create_indexes


async def main() -> None:
    names = await create_indexes()
    print(f"Ensured {len(names)} indexes:")
    for n in names:
        print(f"  - {n}")


if __name__ == "__main__":
    asyncio.run(main())
