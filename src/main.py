import os
import re
import time
import logging
import requests
from flask import Flask, request as flask_request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# ── Credenciales HD-Olimpo ───────────────────────────────────────────────────
HDOLIMPO_BASE_URL = "https://hd-olimpo.club"
HDOLIMPO_USERNAME = os.environ.get('HDOLIMPO_USERNAME')
HDOLIMPO_PASSWORD = os.environ.get('HDOLIMPO_PASSWORD')

# ── Configuración de instancias *arr ─────────────────────────────────────────
ARR_INSTANCES: dict[str, dict] = {
    "Sonarr": {
        "api_url": os.environ.get('SONARR_API_URL'),
        "api_key": os.environ.get('SONARR_API_KEY'),
        "type": "sonarr",
    },
    "Sonarr 4K": {
        "api_url": os.environ.get('SONARR4K_API_URL'),
        "api_key": os.environ.get('SONARR4K_API_KEY'),
        "type": "sonarr",
    },
    "Radarr": {
        "api_url": os.environ.get('RADARR_API_URL'),
        "api_key": os.environ.get('RADARR_API_KEY'),
        "type": "radarr",
    },
    "Radarr 4K": {
        "api_url": os.environ.get('RADARR4K_API_URL'),
        "api_key": os.environ.get('RADARR4K_API_KEY'),
        "type": "radarr",
    },
}

app = Flask(__name__)


# ── Logger ───────────────────────────────────────────────────────────────────
def setup_logger(name: str = 'straperr') -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            f'%(asctime)s - {name} - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


logger = setup_logger()


# ── Helpers de instancia ─────────────────────────────────────────────────────
def get_arr_instance(name: str) -> dict:
    """Devuelve el config dict de la instancia o lanza ValueError."""
    instance = ARR_INSTANCES.get(name)
    if not instance:
        raise ValueError(f"Instancia desconocida: {name!r}")
    return instance


def arr_headers(instance: dict) -> dict:
    return {'X-Api-Key': instance['api_key']}


# ── *Arr API ─────────────────────────────────────────────────────────────────
def get_manual_import(download_id: str, instance_name: str) -> list | None:
    try:
        instance = get_arr_instance(instance_name)
    except ValueError as e:
        logger.error(e)
        return None

    url = (
        f"{instance['api_url']}/manualimport"
        f"?downloadId={download_id}&filterExistingFiles=false"
    )
    response = requests.get(url, headers=arr_headers(instance))

    if response.status_code == 200:
        return response.json()

    logger.error(
        f"GET /manualimport error {response.status_code}: {response.text}"
    )
    return None


def get_languages_for_download(download_id: str, instance_name: str) -> list:
    """Reutiliza get_manual_import en lugar de duplicar la llamada HTTP."""
    import_records = get_manual_import(download_id, instance_name)
    if import_records and import_records[0].get("languages"):
        return import_records[0]["languages"]
    logger.warning(
        "No se encontraron idiomas en la respuesta de manualimport."
    )
    return []


def post_manual_import(
    record: dict, languages: list, instance_name: str
) -> None:
    try:
        instance = get_arr_instance(instance_name)
    except ValueError as e:
        logger.error(e)
        return

    if instance['type'] == 'sonarr':
        files = [{
            "path": record["path"],
            "seriesId": record["episodes"][0]["seriesId"],
            "episodeIds": [record["episodes"][0]["id"]],
            "quality": record["quality"],
            "languages": languages,
            "indexerFlags": 0,
            "releaseType": "singleEpisode",
            "downloadId": record["downloadId"],
        }]
    else:  # radarr
        files = [{
            "path": record["path"],
            "movieId": record["movie"]["id"],
            "quality": record["quality"],
            "languages": languages,
            "downloadId": record["downloadId"],
        }]

    payload = {"name": "ManualImport", "files": files, "importMode": "auto"}
    headers = {**arr_headers(instance), 'Content-Type': 'application/json'}

    logger.info(f"POST ManualImport payload: {payload}")

    response = requests.post(
        f"{instance['api_url']}/command", headers=headers, json=payload
    )
    if response.status_code == 201:
        logger.info(f"ManualImport OK → {record['name']!r}")
    else:
        logger.error(
            f"ManualImport falló para {record['name']!r}: "
            f"{response.status_code} {response.text}"
        )


def delete_queue_items_by_download_id(
    download_id: str, instance_name: str
) -> None:
    try:
        instance = get_arr_instance(instance_name)
    except ValueError as e:
        logger.error(e)
        return

    headers = arr_headers(instance)
    queue_url = f"{instance['api_url']}/queue"

    try:
        response = requests.get(queue_url, headers=headers)
        response.raise_for_status()
        queue = response.json()
        records = (
            queue.get('records', queue) if isinstance(queue, dict) else queue
        )

        for item in records:
            if item.get('downloadId') != download_id:
                continue
            queue_id = item['id']
            delete_url = (
                f"{queue_url}/{queue_id}"
                "?removeFromClient=false&blocklist=false"
                "&skipRedownload=false&changeCategory=false"
            )
            delete_response = requests.delete(delete_url, headers=headers)
            if delete_response.status_code == 200:
                logger.info(
                    f"Queue item {queue_id} eliminado de {instance_name}"
                )
            else:
                logger.error(
                    f"No se pudo eliminar queue item {queue_id}: "
                    f"{delete_response.status_code} {delete_response.text}"
                )
    except Exception as e:
        logger.error(f"Error eliminando items de la cola: {e}")


# ── HD-Olimpo: thanks con Chromium local ─────────────────────────────────────
def build_chrome_driver() -> webdriver.Chrome:
    """
    Configura un Chromium headless instalado en el propio contenedor (paquetes
    Alpine `chromium` + `chromium-chromedriver`), en vez de conectar a un
    contenedor Selenium Grid externo.
    """
    options = Options()
    options.binary_location = os.environ.get(
        'CHROME_BIN', '/usr/bin/chromium-browser'
    )
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')

    service = Service(
        executable_path=os.environ.get(
            'CHROMEDRIVER_PATH', '/usr/bin/chromedriver'
        )
    )
    return webdriver.Chrome(service=service, options=options)


def hdolimpo_thanks(
    username: str,
    password: str,
    search_query: str,
    instance_name: str = 'straperr',
) -> bool:
    """
    Inicia sesión en hd-olimpo.club, busca el torrent y pulsa Agradecer.

    Hace falta un navegador real (no requests + BeautifulSoup) porque el login
    de hd-olimpo.club está protegido por comprobaciones anti-bot (honeypot +
    fingerprint de navegador) que un cliente HTTP puro no supera.
    """
    log = setup_logger(instance_name)

    if not username or not password:
        log.error(
            "Credenciales no configuradas. "
            "Comprueba que HDOLIMPO_USERNAME y HDOLIMPO_PASSWORD "
            "están definidas en el entorno o en el .env"
        )
        return False

    driver = None
    try:
        driver = build_chrome_driver()
        driver.set_page_load_timeout(30)

        # ── 1. Login ─────────────────────────────────────────────────────────
        driver.get(f"{HDOLIMPO_BASE_URL}/login")
        time.sleep(2)

        try:
            username_field = driver.find_element(By.NAME, "username")
            password_field = driver.find_element(By.NAME, "password")
            username_field.send_keys(username)
            password_field.send_keys(password)
            password_field.submit()
        except Exception as e:
            log.error(f"Error rellenando el formulario de login: {e}")
            return False

        time.sleep(3)

        if "Iniciar sesión" in driver.page_source:
            log.error(
                "Login fallido en HD-Olimpo "
                "(credenciales incorrectas o bloqueo anti-bot)."
            )
            return False

        log.info("Login exitoso en HD-Olimpo.")

        # ── 2. Búsqueda del torrent ──────────────────────────────────────────
        driver.get(f"{HDOLIMPO_BASE_URL}/torrents")
        time.sleep(2)

        try:
            search_field = driver.find_element(
                By.XPATH, "//input[@type='search' and @placeholder='Título']")
            search_field.send_keys(search_query)
            log.info(f"Buscando título: {search_query!r}")
            time.sleep(2)
        except Exception as e:
            log.error(f"Error buscando el título: {e}")
            return False

        try:
            torrent_list = driver.find_element(By.ID, "torrent-list-table")
            result_links = torrent_list.find_elements(
                By.XPATH, ".//tbody/tr/td/a"
            )

            result_url = None
            for link in result_links:
                if link.text == search_query:
                    result_url = link.get_attribute("href")
                    log.info(f"Torrent encontrado: {result_url}")
                    break

            if not result_url:
                log.warning(f"Sin coincidencia exacta para {search_query!r}.")
                return False
        except Exception as e:
            log.error(f"Error obteniendo el resultado de búsqueda: {e}")
            return False

        # ── 3. Página del torrent → clic en Agradecer ────────────────────────
        driver.get(result_url)
        time.sleep(2)

        try:
            thanks_button = driver.find_element(
                By.XPATH,
                "//button[contains(@class, 'btn btn-sm btn-primary') "
                "and contains(., 'Agradecer')]")

            if thanks_button.get_attribute("disabled") == "true":
                log.info("Ya habías agradecido este torrent. Sin acción.")
            else:
                thanks_button.click()
                log.info("¡Agradecido correctamente!")

            return True

        except Exception as e:
            log.error(f"Error al interactuar con el botón Agradecer: {e}")
            return False

    except Exception as e:
        log.error(f"Error inesperado en hdolimpo_thanks: {e}")
        return False
    finally:
        if driver is not None:
            driver.quit()


# ── Utilidades ───────────────────────────────────────────────────────────────
def clean_release_title(title: str) -> str:
    pattern = r'\b(MULTi|SPANiSH|Eng)\b\s*|\bENGLiSH\b'

    def replace(m: re.Match) -> str:
        return 'Eng' if m.group(0).lower() == 'english' else ''

    return re.sub(pattern, replace, title, flags=re.IGNORECASE).strip()


# ── Webhook event handlers ───────────────────────────────────────────────────
def handle_test(data: dict, log: logging.Logger):
    instance_name = data.get('instanceName', 'straperr')
    log.info(f"Test de conexión desde {instance_name}")
    return jsonify({
        "status": "success",
        "message": f"Test de {instance_name} recibido correctamente."
    }), 200


def handle_grab(data: dict, log: logging.Logger):
    instance_name = data.get('instanceName', 'straperr')
    title = data.get('movie', {}).get('title', 'Unknown')
    release_title = data.get('release', {}).get('releaseTitle', 'Unknown')
    indexer = data.get('release', {}).get('indexer', 'Unknown')

    clean_title = clean_release_title(release_title)
    log.info(f"Grabando {clean_title!r} desde {indexer}.")
    hdolimpo_thanks(
        HDOLIMPO_USERNAME, HDOLIMPO_PASSWORD, clean_title, instance_name
    )
    return jsonify({
        "status": "success",
        "message": f"{title!r} desde {indexer} grabado correctamente."
    }), 200


def handle_download(data: dict, log: logging.Logger):
    title = data.get('movie', {}).get('title', 'Unknown')
    release_title = data.get('release', {}).get('releaseTitle', 'Unknown')
    indexer = data.get('release', {}).get('indexer', 'Unknown')

    log.info(
        f"Descarga completada: {clean_release_title(release_title)!r} "
        f"desde {indexer}."
    )
    return jsonify({
        "status": "success",
        "message": f"Descargando {title!r} desde {indexer}."
    }), 200


def handle_manual_interaction_required(data: dict, log: logging.Logger):
    instance_name = data.get('instanceName', 'straperr')
    log.info(f"Iniciando importación manual en {instance_name!r}.")
    download_id = data.get('downloadId')

    if not download_id:
        log.error("No se proporcionó downloadId en la petición.")
        return jsonify({
            "status": "error",
            "message": "Se requiere downloadId para continuar."
        }), 400

    languages = get_languages_for_download(download_id, instance_name)
    if not languages:
        languages = [{"id": 3, "name": "Spanish"}]

    records = get_manual_import(download_id, instance_name)
    if records:
        for record in records:
            log.info(f"Procesando: {record['name']}")
            post_manual_import(record, languages, instance_name)
    else:
        log.warning("Sin registros para importación manual.")

    delete_queue_items_by_download_id(download_id, instance_name)

    return jsonify({
        "status": "success",
        "message": "Importación manual completada y cola limpia."
    }), 200


WEBHOOK_HANDLERS = {
    'Test':                      handle_test,
    'Grab':                      handle_grab,
    'Download':                  handle_download,
    'ManualInteractionRequired': handle_manual_interaction_required,
}


# ── Flask routes ─────────────────────────────────────────────────────────────
@app.route('/', methods=['POST'])
def webhook():
    data = flask_request.json
    event_type = data.get('eventType')
    instance_name = data.get('instanceName', 'straperr')

    log = setup_logger(instance_name)

    handler = WEBHOOK_HANDLERS.get(event_type)
    if handler:
        return handler(data, log)

    log.error(f"Tipo de evento desconocido: {event_type!r}")
    return jsonify(
        {"status": "error", "message": "Tipo de evento desconocido."}
    ), 400


@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "OK"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
