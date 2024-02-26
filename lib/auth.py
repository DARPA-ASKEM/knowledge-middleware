"""
Module used to interact with the Terarium Data Service (TDS).
"""

from lib.settings import settings
import requests

TDS_URL = settings.TDS_URL
TDS_USER = settings.TDS_USER
TDS_PASSWORD = settings.TDS_PASSWORD


def auth_session():
	session = requests.Session()
	session.auth = (TDS_USER, TDS_PASSWORD)
	session.headers.update({"Content-Type": "application/json", "X-Enable-Snake-Case": "true"})
	return session
