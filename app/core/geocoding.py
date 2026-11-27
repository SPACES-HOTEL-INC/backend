"""Server-side address geocoding utilities."""

import logging

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


async def geocode_address(
    address: str,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
) -> tuple[float, float] | None:
    """Return (latitude, longitude) for an address using Google Geocoding API."""
    api_key = settings.GOOGLE_MAPS_API_KEY or settings.GOOGLE_API_KEY
    if not api_key:
        logger.warning("Property geocoding skipped: GOOGLE_MAPS_API_KEY is not configured")
        return None

    parts = [address.strip()]
    parts.extend(part.strip() for part in (city, state, country) if part and part.strip())
    query = ", ".join(dict.fromkeys(parts))

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                settings.GOOGLE_MAPS_GEOCODING_URL,
                params={"address": query, "key": api_key},
            )
            response.raise_for_status()
            payload = response.json()

        if payload.get("status") != "OK":
            logger.warning("Geocoding failed for %r: %s", query, payload.get("status"))
            return None

        results = payload.get("results") or []
        if not results:
            return None

        location = results[0].get("geometry", {}).get("location") or {}
        latitude = location.get("lat")
        longitude = location.get("lng")
        if latitude is None or longitude is None:
            return None

        latitude = float(latitude)
        longitude = float(longitude)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return None
        return latitude, longitude
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("Unable to geocode property address %r: %s", query, exc)
        return None
