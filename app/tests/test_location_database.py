"""Database integration smoke test; run against an externally migrated test database."""
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.location_discovery import nearby_events


@pytest.mark.skipif(not os.getenv("ORBIT_TEST_DATABASE_URL"), reason="Migrated PostgreSQL test database unavailable")
def test_nearby_query_runs_on_postgresql():
    engine = create_engine(os.environ["ORBIT_TEST_DATABASE_URL"])
    try:
        with Session(engine) as db:
            items = nearby_events(db, lat=41.0, lon=29.0, radius_km=25)
            assert isinstance(items, list)
            assert all("latitude" not in item and "longitude" not in item for item in items)
    finally:
        engine.dispose()
