import logging
from ask_sdk.standard import StandardSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.utils import is_intent_name
from ask_sdk_core.utils import is_request_type
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import RequestEnvelope
from ask_sdk_model import Response
from ask_sdk_model.services.device_address.address import Address
from ask_sdk_model.services import ServiceException
from ask_sdk_model.ui import AskForPermissionsConsentCard
from ask_sdk_model.ui import LinkAccountCard
from tesla_client import AuthenticationError
from tesla_client import Vehicle
from typing import Callable
from typing import Optional

from tesla_alexa.api_client import AccountNotLinkedError
from tesla_alexa.api_client import TeslaAlexaAccount
from tesla_alexa.api_client import VehicleAsleepError
from tesla_alexa.api_client import get_tesla_account
from tesla_alexa.phrases import status_phrase


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class HomeAddressForbiddenException(Exception):
    """User has not given permissions to access the Alexa device's home address."""


class GetStatusIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (
            is_request_type('LaunchRequest')(handler_input) or
            is_intent_name('GetStatus')(handler_input)
        )

    def handle(self, handler_input: HandlerInput) -> Response:

        try:
            home_address = self.get_home_address(handler_input)
        except HomeAddressForbiddenException:
            handler_input.response_builder.speak(
                'Please enable Location permissions in the Alexa app.'
            ).set_card(
                AskForPermissionsConsentCard(permissions=["read::alexa:device:all:address"])
            ).set_should_end_session(True)
            return handler_input.response_builder.response

        cars = get_cars_from_request(handler_input.request_envelope)

        sentences = [
            status_phrase(car, home_address)
            for car in cars
        ]

        speech_text = ' '.join(sentences)

        handler_input.response_builder.speak(speech_text).set_should_end_session(True)
        return handler_input.response_builder.response

    def get_home_address(self, handler_input: HandlerInput) -> Optional[Address]:
        permissions = handler_input.request_envelope.context.system.user.permissions
        if not (permissions and permissions.consent_token):
            raise HomeAddressForbiddenException

        try:
            device_id = handler_input.request_envelope.context.system.device.device_id
            client = handler_input.service_client_factory.get_device_address_service()
            addr = client.get_full_address(device_id)

            if addr.address_line1 is None and addr.state_or_region is None:
                return None
            else:
                return addr
        except ServiceException:
            return None
        except Exception as e:
            raise e


class CommandIntentHandler(AbstractRequestHandler):
    intent_name = None
    command = None
    prompt_speech = None
    confirm_speech = None
    noop_speech = None

    def can_handle(self, handler_input: HandlerInput) -> bool:
        if is_intent_name(self.intent_name)(handler_input):
            return True
        else:
            parent_intent = handler_input.attributes_manager.session_attributes.get('parent_intent')
            return (
                self.intent_name == parent_intent and
                (
                    is_intent_name('AMAZON.YesIntent')(handler_input) or
                    is_intent_name('AMAZON.NoIntent')(handler_input)
                )
            )
        return False

    def handle(self, handler_input: HandlerInput) -> Response:
        if is_intent_name(self.intent_name)(handler_input):
            car = get_car_by_index(handler_input.request_envelope, 0)

            speech_text = self.prompt_speech.format(car=car.display_name)

            handler_input.attributes_manager.session_attributes = {
                'parent_intent': self.intent_name,
                'car_index': 0,
            }
            handler_input.response_builder.speak(speech_text).set_should_end_session(False)
        elif is_intent_name('AMAZON.YesIntent')(handler_input):
            car_index = handler_input.attributes_manager.session_attributes['car_index']

            car = get_car_by_index(handler_input.request_envelope, car_index)

            status = car.command(self.command)

            if status and status['result']:
                speech_text = self.confirm_speech.format(car=car.display_name)
            else:
                raise VehicleAsleepError(car)

            handler_input.response_builder.speak(speech_text).set_should_end_session(True)
        elif is_intent_name('AMAZON.NoIntent')(handler_input):
            handler_input.attributes_manager.session_attributes['car_index'] += 1
            car_index = handler_input.attributes_manager.session_attributes['car_index']

            car = get_car_by_index(handler_input.request_envelope, car_index)

            if car:
                speech_text = self.prompt_speech.format(car=car.display_name)
                handler_input.response_builder.speak(speech_text).set_should_end_session(False)
            else:
                handler_input.response_builder.speak(self.noop_speech).set_should_end_session(True)
        return handler_input.response_builder.response


class AutoConditioningStartIntentHandler(CommandIntentHandler):
    intent_name = 'AutoConditioningStart'
    command = 'auto_conditioning_start'
    prompt_speech = 'Heat up {car}?'
    confirm_speech = 'Heating up {car}.'
    noop_speech = "I won't heat anything up."


class AutoConditioningStopIntentHandler(CommandIntentHandler):
    intent_name = 'AutoConditioningStop'
    command = 'auto_conditioning_stop'
    prompt_speech = 'Turn off climate control for {car}?'
    confirm_speech = 'Turned off climate control for {car}.'
    noop_speech = "I won't do anything."


class ChargeStartIntentHandler(CommandIntentHandler):
    intent_name = 'ChargeStart'
    command = 'charge_start'
    prompt_speech = 'Start charging {car}?'
    confirm_speech = 'Preparing to charge {car}.'
    noop_speech = "I won't charge anything."


class ChargeStopIntentHandler(CommandIntentHandler):
    intent_name = 'ChargeStop'
    command = 'charge_stop'
    prompt_speech = 'Stop charging {car}?'
    confirm_speech = 'Stopping charing for {car}.'
    noop_speech = "I won't do anything."


class DoorLockIntentHandler(CommandIntentHandler):
    intent_name = 'DoorLock'
    command = 'door_lock'
    prompt_speech = 'Lock {car}?'
    confirm_speech = 'Locking {car}.'
    noop_speech = "I won't do anything."


class DoorUnlockIntentHandler(CommandIntentHandler):
    intent_name = 'DoorUnlock'
    command = 'door_unlock'
    prompt_speech = 'Unlock {car}?'
    confirm_speech = 'Unlocking {car}.'
    noop_speech = "I won't do anything."


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.error(exception, exc_info=True)

        if type(exception) in (AccountNotLinkedError, AuthenticationError):
            handler_input.response_builder.speak(
                'Please log into your Tesla account in the Alexa app.'
            ).set_card(
                LinkAccountCard()
            ).set_should_end_session(
                True
            )
        elif type(exception) == VehicleAsleepError:
            exception.car.wake_up()
            speech = '{} was sleeping. Wait a moment and try again.'.format(exception.car.display_name)
            handler_input.response_builder.speak(speech).set_should_end_session(True)
        else:
            speech = 'Sorry, something went wrong. Goodbye..'
            handler_input.response_builder.speak(speech).set_should_end_session(True)

        return handler_input.response_builder.response


def get_cars_from_request(request: RequestEnvelope) -> TeslaAlexaAccount:
    return get_tesla_account(request.context.system.user.access_token).get_vehicles()


def get_car_by_index(request: RequestEnvelope, index: int) -> Optional[Vehicle]:
    cars = get_cars_from_request(request)
    if cars and len(cars) > index:
        return cars[index]
    else:
        return None


def build_skill() -> Callable:
    sb = StandardSkillBuilder()

    sb.add_request_handler(GetStatusIntentHandler())
    sb.add_request_handler(AutoConditioningStartIntentHandler())
    sb.add_request_handler(AutoConditioningStopIntentHandler())
    sb.add_request_handler(ChargeStartIntentHandler())
    sb.add_request_handler(ChargeStopIntentHandler())
    sb.add_request_handler(DoorLockIntentHandler())
    sb.add_request_handler(DoorUnlockIntentHandler())
    sb.add_exception_handler(CatchAllExceptionHandler())

    return sb.lambda_handler()
