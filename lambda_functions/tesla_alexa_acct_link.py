from uuid import uuid1

from tesla_alexa.api_client import get_tesla_account


def lambda_handler(event, context):
    alexa_access_token = str(uuid1())

    get_tesla_account(alexa_access_token).login(
        event['email'],
        event['password'],
    )

    return {'alexa_access_token': alexa_access_token}
