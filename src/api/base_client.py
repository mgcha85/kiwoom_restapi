# src/api/base_client.py

import requests
from src.config import config

class BaseAPIClient:
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        if self.use_mock:
            self.base_url = config.app.mock_domain
        else:
            self.base_url = config.app.domain

    def post(self, endpoint: str, data: dict, headers: dict = None, extra_headers: dict = None):
        url = self.base_url + endpoint
        default_headers = {
            'Content-Type': 'application/json;charset=UTF-8'
        }
        if headers:
            default_headers.update(headers)
        if extra_headers:
            default_headers.update(extra_headers)
        response = requests.post(url, json=data, headers=default_headers)
        return response
