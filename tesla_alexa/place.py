import googlemaps
import os
from ask_sdk_model.services.device_address.address import Address
from typing import NamedTuple
from typing import Optional


class Place(NamedTuple):
    street_number: str
    street: str
    city: str
    state: str


def get_place(latitude: float, longitude: float) -> Place:
    gmaps = googlemaps.Client(key=os.environ['GOOGLE_API_KEY'])
    results = gmaps.reverse_geocode((latitude, longitude))

    if not results:
        return None

    street_number = None
    street = None
    city = None
    state = None
    for component in results[0]['address_components']:
        if 'street_number' in component['types']:
            street_number = component['short_name']
        elif 'route' in component['types']:
            street = component['short_name']
        elif 'locality' in component['types']:
            city = component['long_name']
        elif 'administrative_area_level_1' in component['types']:
            state = component['short_name']

    return Place(
        street_number=street_number,
        street=street,
        city=city,
        state=state,
    )


def get_travel_time_in_seconds(latitude: float, longitude: float, home_addr: Address) -> Optional[int]:
    gmaps = googlemaps.Client(key=os.environ['GOOGLE_API_KEY'])

    home_addr_str = f'{home_addr.address_line1}, {home_addr.city}, {home_addr.state_or_region}'

    try:
        return gmaps.distance_matrix(
            (latitude, longitude),
            home_addr_str,
            mode='driving',
            units='imperial',
        )['rows'][0]['elements'][0]['duration']['value']
    except (IndexError, KeyError):
        return None
