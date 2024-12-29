# tests/test_grab.py

from common import post_event


# This test simulates the "Grab" event, which occurs when a
# new release is detected and added to the download queue.
test_data = {
    "eventType": "Grab",
    "instanceName": "TestInstance",
    "release": {
        "releaseTitle": "Movie Title [SPANiSH]",
        "indexer": "HD-Olimpo"
    },
    "movie": {
        "title": "Movie Title"
    }
}


if __name__ == "__main__":
    post_event(test_data)
