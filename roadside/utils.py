"""Helper functions for GPS validation and nearby-request filtering."""
import math
from decimal import Decimal, InvalidOperation

EARTH_RADIUS_KM = 6371.0088
NEARBY_RADIUS_KM = 10


def to_float(value):
    """Convert a Decimal/str/float to a finite float, or return None."""
    if value is None or value == "":
        return None
    try:
        number = float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def is_valid_coordinate(lat, lng):
    """True only when both values are real numbers inside the GPS range."""
    lat_f, lng_f = to_float(lat), to_float(lng)
    if lat_f is None or lng_f is None:
        return False
    return -90 <= lat_f <= 90 and -180 <= lng_f <= 180


def calculate_distance(lat1, lon1, lat2, lon2):
    """Great-circle (haversine) distance in kilometres between two points."""
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    d_phi = phi2 - phi1
    d_lambda = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    a = min(1.0, max(0.0, a))
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def distance_to_request(provider, item):
    """Distance in km from provider to request, or None if either has bad GPS."""
    if not is_valid_coordinate(provider.latitude, provider.longitude):
        return None
    if not is_valid_coordinate(item.latitude, item.longitude):
        return None
    return calculate_distance(
        provider.latitude, provider.longitude, item.latitude, item.longitude
    )


def service_matches(provider, item):
    """Does the provider's service type suit what the customer needs?"""
    return (
        item.service_needed == "EITHER"
        or provider.service_type == "BOTH"
        or item.service_needed == provider.service_type
    )


def nearby_open_requests(provider, radius_km=NEARBY_RADIUS_KM):
    """Open, unassigned, compatible requests within radius_km of the provider.

    Requests this provider already rejected are left out. Each returned
    request gets a ``distance_km`` attribute and the list is sorted nearest
    first. Providers that are unavailable or have no valid GPS get [].
    """
    from .models import AssistanceRequest  # local import avoids a cycle

    if not provider.is_available:
        return []
    if not is_valid_coordinate(provider.latitude, provider.longitude):
        return []

    candidates = (
        AssistanceRequest.objects.filter(status="OPEN", provider__isnull=True)
        .exclude(rejections__provider=provider)
        .select_related("customer")
    )

    results = []
    for item in candidates:
        if not service_matches(provider, item):
            continue
        distance = distance_to_request(provider, item)
        if distance is None or distance > radius_km:
            continue
        item.distance_km = round(distance, 1)
        results.append(item)

    results.sort(key=lambda r: r.distance_km)
    return results
