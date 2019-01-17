from ask_sdk_model.services.device_address.address import Address
from tesla_client import Vehicle
from typing import Optional

from tesla_alexa.place import get_place
from tesla_alexa.place import get_travel_time_in_seconds
from tesla_alexa.place import Place


def status_phrase(car: Vehicle, home_addr: Address) -> str:
    vehicle_data = car.get_vehicle_data()

    if not vehicle_data:
        return wake_up_and_retry(car)

    car_name = car.display_name
    drive_state = vehicle_data['drive_state']
    charge_state = vehicle_data['charge_state']

    location_phr = location_phrase(
        drive_state['latitude'],
        drive_state['longitude'],
        home_addr,
    ) if drive_state else None

    sentences = []

    if drive_state['shift_state'] == 'D':
        speed = drive_state['speed']

        if speed:
            heading_phr = heading_phrase(drive_state['heading'])
            if location_phr:
                sentences.append(
                    f"{car_name} is {location_phr}, heading {heading_phr} at {speed} miles per hour.",
                )
            else:
                sentences.append(
                    f"{car_name} is heading {heading_phr} at {speed} miles per hour.",
                )
        else:
            if location_phr:
                sentences.append(f"{car_name} is stopped {location_phr}.")
            else:
                sentences.append(f"{car_name} is stopped.")
    else:
        if charge_state['charging_state'] == 'Charging':
            time_left_phr = hours_or_minutes_phrase(charge_state['time_to_full_charge'])
            charging_phr = 'supercharging' if charge_state['fast_charger_present'] else 'charging'

            if location_phr and location_phr != 'at home':
                sentences.append(
                    f"{car_name} is {location_phr} and {charging_phr} with {time_left_phr} to go.",
                )
            else:
                sentences.append(
                    f"{car_name} is {charging_phr} with {time_left_phr} to go.",
                )
        elif charge_state['charging_state'] == 'Complete':
            if location_phr and location_phr != 'at home':
                sentences.append(f"{car_name} is {location_phr} and done charging.")
            else:
                sentences.append(f"{car_name} is done charging.")
        elif charge_state['charging_state'] == 'Disconnected':
            if location_phr and location_phr == 'at home':
                sentences.append(f"{car_name} is unplugged.")
            elif location_phr:
                sentences.append(f"{car_name} is parked {location_phr}.")
            else:
                sentences.append(f"{car_name} is parked.")
        elif charge_state['charging_state'] == 'Stopped':
            if location_phr and location_phr != 'at home':
                sentences.append(f"{car_name} is plugged in and ready to charge {location_phr}.")
            else:
                sentences.append(f"{car_name} is plugged in and ready to charge.")
        else:
            if location_phr:
                sentences.append(f"Charging state is {charge_state['charging_state']} {location_phr}.")
            else:
                sentences.append(f"Charging state is {charge_state['charging_state']}.")

    sentences.append(f"Available range is {int(charge_state['battery_range'])} miles.")

    return ' '.join(sentences)


def wake_up_and_retry(car: Vehicle) -> str:
    car.wake_up()
    return f"{car.display_name} was sleeping. Wait a moment and try again."


def hours_or_minutes_phrase(hours_decimal: float) -> str:
    minutes = round(hours_decimal % 1 * 60)

    if hours_decimal > 1.0:
        return '<say-as interpret-as="unit">{}h</say-as>'.format(round(hours_decimal))
    else:
        return'<say-as interpret-as="unit">{}min</say-as>'.format(minutes)


def hours_and_minutes_phrase(seconds: int) -> str:
    hours = int(seconds / 3600)
    minutes = int(seconds % 3600 / 60)

    if hours and minutes:
        return (
            '<say-as interpret-as="unit">{}h</say-as> and '
            '<say-as interpret-as="unit">{}min</say-as>'
        ).format(hours, minutes)
    elif hours:
        return '<say-as interpret-as="unit">{}h</say-as>'.format(hours)
    else:
        return '<say-as interpret-as="unit">{}min</say-as>'.format(minutes)


def place_phrase(place: Place) -> Optional[str]:
    if not place:
        return ''

    segs = []
    if place.street:
        segs.append('<say-as interpret-as="address">{}</say-as>'.format(place.street))
    if place.city:
        segs.append('<say-as interpret-as="address">{}</say-as>'.format(
            place.city if place.state == 'CA' else '{}, {}'.format(place.city, place.state)
        ))

    if segs:
        return 'on ' + ' in '.join(segs)
    else:
        return None


def location_phrase(latitude: float, longitude: float, home_addr: Address) -> Optional[str]:
    travel_time = get_travel_time_in_seconds(latitude, longitude, home_addr) if home_addr else None

    if travel_time is not None and travel_time <= 60:
        return "at home"
    else:
        place = get_place(latitude, longitude)
        if place and travel_time is None:
            return place_phrase(place)
        elif place:
            return f"{hours_and_minutes_phrase(travel_time)} away {place_phrase(place)}"
        else:
            return None


def heading_phrase(heading: float) -> str:
    for degrees, heading_name in (
        (22.5, 'north'),
        (67.5, 'northeast'),
        (112.5, 'east'),
        (157.5, 'southeast'),
        (202.5, 'south'),
        (247.5, 'southwest'),
        (292.5, 'west'),
        (337.5, 'northwest'),
        (360, 'north'),
    ):
        if heading < degrees:
            return heading_name
