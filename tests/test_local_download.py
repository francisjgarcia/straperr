# tests/test_download.py

from common import post_event


# This test simulates the "Download" event, which
# occurs when a release has started downloading.
test_data = {
    "eventType": "Download",
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
