import boto3
import os

import tesla_client


def get_tesla_account(alexa_access_token):
    tesla_client.init(
        os.environ['CLIENT_ID'],
        os.environ['CLIENT_SECRET'],
    )
    return TeslaAlexaAccount(alexa_access_token)


class AccountNotLinkedError(Exception):
    """Unable to authenticate"""


class VehicleAsleepError(Exception):
    """Vehicle was asleep"""
    def __init__(self, car):
        self.car = car


class TeslaAlexaAccount(tesla_client.Account):
    def __init__(self, alexa_access_token):
        self.alexa_access_token = alexa_access_token

    def get_credentials(self):
        resp = get_oauth_table().get_item(Key={'id': self.alexa_access_token})
        if 'Item' not in resp:
            raise AccountNotLinkedError

        creds = resp['Item']

        return tesla_client.OAuthCredentials(
            access_token=creds['access_token'],
            refresh_token=creds['refresh_token'],
            token_expiry=creds['token_expiry'],
        )

    def save_credentials(self, creds):
        creds_dict = dict(
            id=self.alexa_access_token,
            **creds._asdict()
        )
        get_oauth_table().put_item(Item=creds_dict)


def get_oauth_table():
    return boto3.resource('dynamodb').Table('tesla_oauth')
