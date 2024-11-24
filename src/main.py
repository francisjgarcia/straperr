
import os
import time
import re
import logging
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

HDOLIMPO_USERNAME = os.environ.get('HDOLIMPO_USERNAME')
HDOLIMPO_PASSWORD = os.environ.get('HDOLIMPO_PASSWORD')

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


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
        print(f"Error filling out login fields: {str(e)}")
        driver.quit()
        return

    # Wait to ensure the login process completes
    time.sleep(3)

    # Check if login was successful
    try:
        if "Iniciar sesión" in driver.page_source:
            print("Login failed. Could not find the success text.")
            print("Login page content:")
            print(driver.page_source)  # Print the HTML content for debugging
            driver.quit()
            return
        else:
            print("Login successful!")
    except Exception as e:
        print(f"Error checking login status: {str(e)}")
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
        print(f"Error searching for the title: {str(e)}")
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
                print(f"URL of the first matching result: {result_url}")
                break
        else:
            print("No matching result found.")
            driver.quit()
            return

    except Exception as e:
        print(f"Error getting the result: {str(e)}")
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
            print(
                "You have already thanked for this torrent. "
                "No action taken.")
        else:
            # If the button is not disabled, click the 'Thank You' button
            thanks_button.click()
            print("Thanked successfully!")

    except Exception as e:
        print(f"Error interacting with the 'Thank You' button: {str(e)}")

    # Close the browser session
    driver.quit()


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
        hdolimpo_thanks(HDOLIMPO_USERNAME, HDOLIMPO_PASSWORD,
                        f'{clean_release_title}')
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
