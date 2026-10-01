from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.event import EventCreate


def test_event_coordinate_validation():
    now = datetime.now(UTC)
    values = dict(group_id=uuid4(), title="Konser", location="İstanbul",
                  start_time=now, end_time=now + timedelta(hours=1))
    assert EventCreate(**values, latitude=41, longitude=29).latitude == 41
    with pytest.raises(ValidationError):
        EventCreate(**values, latitude=91, longitude=29)
    with pytest.raises(ValidationError):
        EventCreate(**values, latitude=41, longitude=181)
    with pytest.raises(ValidationError):
        EventCreate(**values, latitude=41)


def test_group_coordinates_are_validated_and_not_exposed_in_group_read():
    from app.schemas.group import GroupCreate, GroupRead

    assert GroupCreate(name="Semt", latitude=41, longitude=29).longitude == 29
    with pytest.raises(ValidationError):
        GroupCreate(name="Semt", latitude=-91, longitude=29)
    assert "latitude" not in GroupRead.model_fields
    assert "longitude" not in GroupRead.model_fields
