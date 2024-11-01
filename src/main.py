import re
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


# Main endpoint
@app.route('/', methods=['POST'])
def main():
    data = request.json
    event_type = data.get('eventType')
    instance_name = data.get('instanceName', 'Unknown')
    title = data.get('movie', {}).get('title', 'Unknown')
    release_title = data.get('release', {}).get('releaseTitle',
                                                'Unknown')
    indexer = data.get('release', {}).get('indexer', 'Unknown')

    # Remove [SPANiSH] from release title
    clean_release_title = re.sub(
        r'\s*\[?\bSPANiSH\b\]?\s*$',
        '', release_title, flags=re.IGNORECASE)

    # Define functions for each event case
    def handle_test():
        app.logger.info(f"Test connection from {instance_name}")
        return jsonify({
            "status": "success",
            "message": (f"Connection test from {instance_name} "
                        "received successfully.")
        }), 200

    def handle_grab():
        app.logger.info(f"Grabbing '{clean_release_title}' "
                        f"from {indexer}.")
        return jsonify({
            "status": "success",
            "message": (f"Title '{title}' "
                        f"from {indexer} grabbed successfully.")
        }), 200

    def handle_download():
        app.logger.info(f"Downloading '{clean_release_title}' from {indexer}.")
        return jsonify({
            "status": "success",
            "message": (f"Downloading '{title}' "
                        f"from {indexer} successfully.")
        }), 200

    # Dictionary that acts as a switch
    event_handlers = {
        "Test": handle_test,
        "Grab": handle_grab,
        "Download": handle_download,
    }

    # Run the corresponding function for the event, if it exists
    handler = event_handlers.get(event_type)

    if handler:
        return handler()
    else:
        app.logger.warning(f"Event type not supported: {event_type}")
        app.logger.info(data)
        return jsonify({
            "status": "error",
            "message": "Event type not supported"
        }), 400


# Status healthcheck endpoint
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "OK"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
