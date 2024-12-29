# tests/common.py

import requests
import json

API_URL = "http://localhost:5000"


def post_event(data):
    """
    Sends a POST request with the provided event data to the Flask server.

    Parameters:
    data (dict): The JSON payload representing the event.
    """
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.post(f"{API_URL}/",
                             headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        print(f"Test passed: {response.json()}")
    else:
        print("Test failed with status code "
              f"{response.status_code}: {response.text}")
