"""
F5-2: Google Maps Places API client — scoring reputational real.
Foloseste Places API (Legacy) - Find Place from Text endpoint.
Free tier: $200 credit/luna (~28.500 req/luna pe plan Pay-as-you-go).
"""

import asyncio

from loguru import logger

from backend.config import settings
from backend.http_client import get_client

_FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
_PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


async def get_maps_rating(company_name: str, address: str = "") -> dict:
    """
    Cauta o firma pe Google Maps si returneaza rating + numar recenzii.

    Returns:
        {
            "found": bool,
            "name": str,
            "rating": float | None,
            "reviews_count": int,
            "place_id": str,
            "address": str,
            "source": "google_maps"
        }
    """
    key = settings.google_cloud_api_key
    if not key:
        return {"found": False, "error": "GOOGLE_CLOUD_API_KEY neconfigurat", "source": "google_maps"}

    query = f"{company_name} {address} Romania".strip()

    try:
        client = get_client()
        params = {
            "input": query,
            "inputtype": "textquery",
            "fields": "name,rating,user_ratings_total,place_id,formatted_address",
            "language": "ro",
            "key": key,
        }
        r = await asyncio.wait_for(
            client.get(_FIND_PLACE_URL, params=params),
            timeout=10.0,
        )
        data = r.json()
        status = data.get("status", "UNKNOWN")

        if status == "OK":
            candidate = data.get("candidates", [{}])[0]
            rating = candidate.get("rating")
            reviews = candidate.get("user_ratings_total", 0)
            return {
                "found": True,
                "name": candidate.get("name", company_name),
                "rating": rating,
                "reviews_count": reviews,
                "place_id": candidate.get("place_id", ""),
                "address": candidate.get("formatted_address", ""),
                "source": "google_maps",
            }
        elif status == "ZERO_RESULTS":
            return {"found": False, "error": "no_results", "source": "google_maps"}
        elif status == "REQUEST_DENIED":
            logger.warning(f"[maps] REQUEST_DENIED: {data.get('error_message','?')}")
            return {"found": False, "error": "request_denied", "source": "google_maps"}
        else:
            logger.debug(f"[maps] status={status}")
            return {"found": False, "error": status.lower(), "source": "google_maps"}

    except TimeoutError:
        return {"found": False, "error": "timeout", "source": "google_maps"}
    except Exception as e:
        logger.debug(f"[maps] error: {e}")
        return {"found": False, "error": str(e), "source": "google_maps"}


def score_from_rating(maps_result: dict) -> int:
    """
    Calculeaza bonus/malus pentru scoring reputational din date Google Maps.

    Returns:
        int: +15 (rating >=4.0, >=10 recenzii) | +5 (rating >=3.5) | -10 (rating <3.0) | 0 (altfel)
    """
    if not maps_result.get("found"):
        return 0

    rating = maps_result.get("rating")
    reviews = maps_result.get("reviews_count", 0)

    if rating is None:
        return 0

    if rating >= 4.0 and reviews >= 10:
        return 15
    elif rating >= 3.5:
        return 5
    elif rating < 3.0 and reviews >= 5:
        return -10
    return 0
