import requests
import os
from django.conf import settings

class MTNMomoClient:
    def __init__(self, api_user, api_key, subscription_key, base_url, target_env):
        self.api_user = api_user
        self.api_key = api_key
        self.subscription_key = subscription_key
        self.base_url = base_url
        self.target_env = target_env
        self.token = None

    def get_token(self, product='collection'):
        url = f'{self.base_url}/{product}/token/'
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
        }
        data = {
            'X-Reference-Id': self.api_user,
            'X-Api-Key': self.api_key,
        }
        resp = requests.post(url, headers=headers, data=data)
        resp.raise_for_status()
        self.token = resp.json()['access_token']
        return self.token

    def get_headers(self, product='collection'):
        if not self.token:
            self.get_token(product)
        return {
            'Authorization': f'Bearer {self.token}',
            'X-Target-Environment': self.target_env,
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json',
        } 