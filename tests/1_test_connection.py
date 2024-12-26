# tests/test_connection.py

from common import post_event


# This test simulates the "Test" event, which checks the connection.
test_data = {
    "eventType": "Test",
    "instanceName": "TestInstance"
}


if __name__ == "__main__":
    post_event(test_data)
