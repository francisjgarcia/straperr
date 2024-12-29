import os
import time
import re
import logging
import requests
import json
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# HD-Olimpo credentials
HDOLIMPO_USERNAME = os.environ.get('HDOLIMPO_USERNAME')
HDOLIMPO_PASSWORD = os.environ.get('HDOLIMPO_PASSWORD')

# Sonarr credentials
SONARR_API_URL = os.environ.get('SONARR_API_URL')
SONARR_API_KEY = os.environ.get('SONARR_API_KEY')

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


# Function to get the manual import data from Sonarr using downloadId
def get_manual_import(download_id):
    headers = {
        'X-Api-Key': SONARR_API_KEY
    }
    url = (
        f"{SONARR_API_URL}/manualimport?downloadId={download_id}&"
        "filterExistingFiles=false"
    )

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()  # Return the JSON response
    else:
        app.logger.error(
            f"Error in GET: {response.status_code} - {response.text}")
        return None


# New function to get languages from the new endpoint using downloadId
def get_languages_for_download(download_id):
    headers = {
        'X-Api-Key': SONARR_API_KEY
    }
    url = (
        f"{SONARR_API_URL}/manualimport?downloadId={download_id}&"
        "filterExistingFiles=false"
    )
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        if data and len(data) > 0 and "languages" in data[0]:
            return data[0]["languages"]
        else:
            app.logger.warning("No languages found in response.")
            return []
    else:
        app.logger.error(f"Error fetching languages: {response.status_code}")
        return []


# Function to perform the POST with the data from the GET
def post_manual_import(data, languages):
    headers = {
        'X-Api-Key': SONARR_API_KEY,
        'Content-Type': 'application/json'
    }

    post_data = {
        "name": "ManualImport",
        "files": [
            {
                "path": data["path"],
                "seriesId": data["episodes"][0]["seriesId"],
                "episodeIds": [data["episodes"][0]["id"]],
                "quality": data["quality"],
                "languages": languages,
                "indexerFlags": 0,
                "releaseType": "singleEpisode",
                "downloadId": data["downloadId"]
            }
        ],
        "importMode": "auto"
    }

    app.logger.info(f"POST data: {post_data}")

    response = requests.post(
        f"{SONARR_API_URL}/command",
        headers=headers, data=json.dumps(post_data))

    if response.status_code == 201:
        app.logger.info(f"Successfully posted for {data['name']}")
    else:
        app.logger.error(
            f"Error in POST for {data['name']}: {response.status_code}")
        app.logger.error(response.text)


# Function to perform the POST with the data from the GET
def hdolimpo_thanks(username, password, search_query):
    """
    Logs in to the website, searches for the specified torrent,
    and clicks the 'Thank You' button if it hasn't been clicked already.

    Parameters:
    - username: The username for login.
    - password: The password for login.
    - search_query: The title of the torrent to search for.
    """

    # URL for login and search
    login_url = "https://hd-olimpo.club/login"
    search_url = "https://hd-olimpo.club/torrents"

    # Configure the Selenium WebDriver for headless mode
    options = Options()
    options.headless = True  # Set to False if you want to see the browser

    # Create the Selenium driver (connected to Selenium Grid)
    driver = webdriver.Remote(
        command_executor='http://straperr-selenium:4444/wd/hub',
        options=options
    )

    # Access the login page
    driver.get(login_url)
    time.sleep(2)  # Wait for the login page to load

    # Fill in the username and password and log in
    try:
        # Find the username and password input fields
        username_field = driver.find_element(By.NAME, "username")
        password_field = driver.find_element(By.NAME, "password")
        username_field.send_keys(username)
        password_field.send_keys(password)

        # Submit the login form
        password_field.submit()

    except Exception as e:
        app.logger.error(f"Error filling out the login fields: {str(e)}")
        driver.quit()
        return

    # Wait to ensure the login process completes
    time.sleep(3)

    # Check if login was successful
    try:
        if "Iniciar sesión" in driver.page_source:
            app.logger.error("Login failed. Could not find the success text.")
            app.logger.info("Login page content:")
            app.logger.info(driver.page_source)
            driver.quit()
            return
        else:
            app.logger.info(
                "Login successful at HD-Olimpo. User authenticated.")
    except Exception as e:
        app.logger.error(f"Error checking login status: {str(e)}")
        driver.quit()
        return

    # Navigate to the torrents page
    driver.get(search_url)
    time.sleep(2)

    # Search for the specified title
    try:
        search_field = driver.find_element(
            By.XPATH, "//input[@type='search' and @placeholder='Título']")
        search_field.send_keys(search_query)
        time.sleep(2)  # Wait for results to load
    except Exception as e:
        app.logger.error(f"Error searching for the title: {str(e)}")
        driver.quit()
        return

    # Find the first result that matches the search query
    try:
        torrent_list = driver.find_element(By.ID, "torrent-list-table")

        # Find all links in the table
        result_links = torrent_list.find_elements(By.XPATH, ".//tbody/tr/td/a")

        # Loop through the links and find the matching title
        for link in result_links:
            if link.text == search_query:
                # If the link text matches, get the URL of the torrent
                result_url = link.get_attribute("href")
                app.logger.info(
                    f"URL of the first matching result: {result_url}")
                break
        else:
            app.logger.warning(
                f"No matching result found for '{search_query}'.")
            driver.quit()
            return

    except Exception as e:
        app.logger.error(f"Error getting the result: {str(e)}")
        driver.quit()
        return

    # Access the obtained URL
    driver.get(result_url)
    time.sleep(2)

    # Check if the 'Thank You' button is disabled (already thanked)
    try:
        thanks_button = driver.find_element(
            By.XPATH, "//button[contains(@class, 'btn btn-sm btn-primary') "
            "and contains(., 'Agradecer')]")

        # Check if the button has the 'disabled' attribute
        if thanks_button.get_attribute("disabled") == "true":
            app.logger.info(
                "You have already thanked for this torrent. No action taken.")
        else:
            # If the button is not disabled, click the 'Thank You' button
            thanks_button.click()
            app.logger.info("Successfully thanked!")

    except Exception as e:
        app.logger.error(
            f"Error interacting with the 'Thank You' button: {str(e)}")

    # Close the browser session
    driver.quit()


# Function to clean the release title
def clean_release_title(title):
    patron = r'\b(MULTi|SPANiSH)\b\s*|\bENGLiSH\b'

    def reemplazo(match):
        if match.group(0).lower() == 'english':
            return 'Eng'
        return ''

    return re.sub(patron, reemplazo, title, flags=re.IGNORECASE).strip()


# Main endpoint
@app.route('/', methods=['POST'])
def main():
    data = request.json
    event_type = data.get('eventType')
    instance_name = data.get('instanceName', 'Unknown')
    title = data.get('movie', {}).get('title', 'Unknown')
    release_title = data.get('release', {}).get('releaseTitle', 'Unknown')
    indexer = data.get('release', {}).get('indexer', 'Unknown')

    # Define functions for each event case
    def handle_test():
        app.logger.info(f"Test connection from {instance_name}")
        return jsonify({
            "status": "success",
            "message": (f"Connection test from {instance_name} "
                        "received successfully.")
        }), 200

    def handle_grab():
        app.logger.info(
            f"Grabbing '{clean_release_title(release_title)}' from {indexer}.")
        return jsonify({
            "status": "success",
            "message": (f"Title '{title}' "
                        f"from {indexer} grabbed successfully.")
        }), 200

    def handle_download():
        app.logger.info(
            f"Downloading '{clean_release_title(release_title)}'"
            f"from {indexer}.")
        hdolimpo_thanks(
            HDOLIMPO_USERNAME, HDOLIMPO_PASSWORD,
            f'{clean_release_title(release_title)}')

        return jsonify({
            "status": "success",
            "message": (f"Downloading '{title}' "
                        f"from {indexer} successfully.")
        }), 200

    def handle_manual_interaction_required():
        app.logger.info(
            f"Starting manual import process to '{instance_name}'.")

        download_id = data.get('downloadId', {})

        if not download_id:
            app.logger.error("No downloadId provided in the request.")
            return jsonify({
                "status": "error",
                "message": "downloadId is required to continue."
            }), 400

        languages = get_languages_for_download(data["downloadId"])

        if not languages:
            languages = [{"id": 3, "name": "Spanish"}]

        manual_import_data = get_manual_import(download_id)

        if manual_import_data:
            for record in manual_import_data:
                app.logger.info(f"Processing: {record['name']}")
                post_manual_import(record, languages)
        else:
            app.logger.warning("No records found or error in manual import.")

        return jsonify({
            "status": "success",
            "message": "Manual import process completed."
        }), 200

    # Dictionary that acts as a switch
    event_handlers = {
        'Test': handle_test,
        'Grab': handle_grab,
        'Download': handle_download,
        'ManualInteractionRequired': handle_manual_interaction_required,
    }

    # Run the corresponding function for the event, if it exists
    handler = event_handlers.get(event_type)

    if handler:
        return handler()
    else:
        app.logger.error(f"Unknown event type: {event_type}")
        return jsonify({
            "status": "error",
            "message": "Unknown event type."
        }), 400


# Status healthcheck endpoint
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "OK"}), 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
