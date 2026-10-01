from math import cos, radians

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.group import Group


def nearby_events(db: Session, *, lat: float, lon: float, radius_km: float, category: str | None = None) -> list[dict]:
    # A bounding box lets the coordinate index reduce the candidate set.
    lat_delta = radius_km / 111.195
    lon_delta = min(180.0, radius_km / max(0.01, 111.195 * abs(cos(radians(lat)))))
    latitude = func.radians(Event.latitude)
    longitude = func.radians(Event.longitude)
    haversine = func.power(func.sin((latitude - radians(lat)) / 2), 2) + (
        cos(radians(lat)) * func.cos(latitude) * func.power(func.sin((longitude - radians(lon)) / 2), 2)
    )
    distance = (2 * 6371.0088 * func.asin(func.sqrt(func.least(1.0, haversine)))).label("distance_km")
    if lon_delta >= 180:
        longitude_filter = Event.longitude.is_not(None)
    elif lon - lon_delta < -180:
        longitude_filter = or_(
            Event.longitude >= lon - lon_delta + 360,
            Event.longitude <= lon + lon_delta,
        )
    elif lon + lon_delta > 180:
        longitude_filter = or_(
            Event.longitude >= lon - lon_delta,
            Event.longitude <= lon + lon_delta - 360,
        )
    else:
        longitude_filter = Event.longitude.between(lon - lon_delta, lon + lon_delta)
    stmt = (
        select(Event, distance)
        .join(Group, Group.id == Event.group_id)
        .where(
            Event.latitude.between(max(-90, lat - lat_delta), min(90, lat + lat_delta)),
            longitude_filter,
        )
    )
    if category:
        stmt = stmt.where(Group.category == category)
    rows = db.execute(stmt.order_by(distance).limit(200)).all()
    return [{"id": event.id, "title": event.title, "description": event.description,
             "starts_at": event.start_time, "location": event.location, "city": event.city,
             "distance_km": round(float(km)), "group_id": event.group_id}
            for event, km in rows if float(km) <= radius_km]
