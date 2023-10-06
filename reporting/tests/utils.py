import os

import requests

KM_URL = os.environ.get(
    "KNOWLEDGE_MIDDLEWARE_URL", "http://knowledge-middleware-api:8000"
)


def post_to_km_endpoint(endpoint, json=None, params=None, data=None):
    return requests.post(KM_URL + endpoint, json=json, params=params, data=data)
