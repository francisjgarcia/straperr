import os
import re
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
from flask import Flask, request as flask_request, jsonify

# ── Credenciales HD-Olimpo ───────────────────────────────────────────────────
HDOLIMPO_BASE_URL = "https://hd-olimpo.club"
HDOLIMPO_USERNAME = os.environ.get('HDOLIMPO_USERNAME')
HDOLIMPO_PASSWORD = os.environ.get('HDOLIMPO_PASSWORD')
HDOLIMPO_TIMEOUT = 30
HDOLIMPO_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"
)

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


# ── HD-Olimpo: thanks vía HTTP ───────────────────────────────────────────────
def normalize_whitespace(text: str) -> str:
    return ' '.join(text.split())


def hdolimpo_login(
    session: requests.Session,
    username: str,
    password: str,
    log: logging.Logger,
) -> bool:
    """
    Inicia sesión en hd-olimpo.club (UNIT3D).

    El login está protegido por el HiddenCaptcha de UNIT3D, que se valida por
    completo en el servidor: un token cifrado `_captcha` (ligado a sesión, IP
    y User-Agent), un honeypot `_username` que debe llegar presente y vacío,
    y un campo de nombre aleatorio cuyo valor es el timestamp del token. Basta
    con reenviar todos los inputs del formulario tal cual, con la misma
    sesión y User-Agent del GET.
    """
    response = session.get(
        f"{HDOLIMPO_BASE_URL}/login", timeout=HDOLIMPO_TIMEOUT
    )
    response.raise_for_status()

    form = BeautifulSoup(response.text, 'html.parser').select_one(
        'form[action$="/login"]'
    )
    if form is None:
        log.error("No se encontró el formulario de login de HD-Olimpo.")
        return False

    data = {
        field['name']: field.get('value', '')
        for field in form.find_all('input', attrs={'name': True})
        if field.get('type') != 'checkbox'
    }
    data['username'] = username
    data['password'] = password

    # Margen por si el captcha exige un tiempo mínimo entre render y envío.
    time.sleep(2)

    response = session.post(
        f"{HDOLIMPO_BASE_URL}/login",
        data=data,
        headers={'Referer': f"{HDOLIMPO_BASE_URL}/login"},
        timeout=HDOLIMPO_TIMEOUT,
    )
    response.raise_for_status()

    if response.url.rstrip('/').endswith('/login'):
        log.error(
            "Login fallido en HD-Olimpo "
            "(credenciales incorrectas o captcha rechazado)."
        )
        return False

    log.info("Login exitoso en HD-Olimpo.")
    return True


def hdolimpo_find_torrent(
    session: requests.Session, search_query: str, log: logging.Logger
) -> str | None:
    """Devuelve la URL del torrent cuyo nombre coincide exactamente."""
    response = session.get(
        f"{HDOLIMPO_BASE_URL}/torrents",
        params={'name': search_query},
        timeout=HDOLIMPO_TIMEOUT,
    )
    response.raise_for_status()
    log.info(f"Buscando título: {search_query!r}")

    wanted = normalize_whitespace(search_query)
    soup = BeautifulSoup(response.text, 'html.parser')
    for link in soup.select('a.torrent-search--list__name'):
        if normalize_whitespace(link.get_text()) == wanted:
            log.info(f"Torrent encontrado: {link['href']}")
            return link['href']

    log.warning(f"Sin coincidencia exacta para {search_query!r}.")
    return None


def hdolimpo_click_thanks(
    session: requests.Session, torrent_url: str, log: logging.Logger
) -> bool:
    """
    Pulsa "Agradecer" en la página del torrent.

    El botón es un componente Livewire 3 (`thank-button`): pulsarlo equivale
    a un POST JSON al endpoint de update de Livewire con el snapshot del
    componente y la llamada de su `wire:click` (p. ej. `store(77444)`).
    """
    response = session.get(torrent_url, timeout=HDOLIMPO_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Otros componentes (p. ej. bookmark-button) también usan store(<id>),
    # así que se identifica el botón por el nombre del componente.
    button = None
    for candidate in soup.find_all('button', attrs={'wire:snapshot': True}):
        memo = json.loads(candidate['wire:snapshot']).get('memo', {})
        if memo.get('name') == 'thank-button':
            button = candidate
            break

    if button is None:
        log.error("No se encontró el botón Agradecer en la página.")
        return False

    config = re.search(
        r'window\.livewireScriptConfig\s*=\s*(\{.*?\});', response.text
    )
    call = re.fullmatch(r'\s*(\w+)\((.*)\)\s*', button.get('wire:click', ''))
    if not config or not call:
        log.error(
            "No se pudo leer la configuración de Livewire "
            "o la acción del botón Agradecer."
        )
        return False

    livewire = json.loads(config.group(1))
    payload = {
        '_token': livewire['csrf'],
        'components': [{
            'snapshot': button['wire:snapshot'],
            'updates': {},
            'calls': [{
                'path': '',
                'method': call.group(1),
                'params': json.loads(f"[{call.group(2)}]"),
            }],
        }],
    }

    response = session.post(
        f"{HDOLIMPO_BASE_URL}{livewire['uri']}",
        json=payload,
        headers={'X-Livewire': 'true', 'Referer': torrent_url},
        timeout=HDOLIMPO_TIMEOUT,
    )
    if response.status_code != 200:
        log.error(
            f"Livewire respondió {response.status_code} al agradecer: "
            f"{response.text[:300]}"
        )
        return False

    # El resultado llega como un toast de Livewire:
    #   success → {'message': 'Your thank was successfully applied!'}
    #   error   → {'message': 'You have already thanked!'} (u otro motivo)
    effects = response.json()['components'][0].get('effects', {})
    for event in effects.get('dispatches', []):
        message = event.get('params', {}).get('message', '')
        if event.get('name') == 'success':
            log.info(f"¡Agradecido correctamente! ({message})")
            return True
        if event.get('name') == 'error':
            if 'already' in message.lower():
                log.info("Ya habías agradecido este torrent. Sin acción.")
                return True
            log.error(f"HD-Olimpo rechazó el agradecimiento: {message}")
            return False

    log.warning(
        "Respuesta de Livewire sin confirmación de éxito ni error; "
        "no se sabe si el agradecimiento se aplicó."
    )
    return False


def hdolimpo_thanks(
    username: str,
    password: str,
    search_query: str,
    instance_name: str = 'straperr',
) -> bool:
    """Inicia sesión en hd-olimpo.club, busca el torrent y pulsa Agradecer."""
    log = setup_logger(instance_name)

    if not username or not password:
        log.error(
            "Credenciales no configuradas. "
            "Comprueba que HDOLIMPO_USERNAME y HDOLIMPO_PASSWORD "
            "están definidas en el entorno o en el .env"
        )
        return False

    try:
        with requests.Session() as session:
            session.headers['User-Agent'] = HDOLIMPO_USER_AGENT

            if not hdolimpo_login(session, username, password, log):
                return False

            torrent_url = hdolimpo_find_torrent(session, search_query, log)
            if not torrent_url:
                return False

            return hdolimpo_click_thanks(session, torrent_url, log)

    except Exception as e:
        log.error(f"Error inesperado en hdolimpo_thanks: {e}")
        return False


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
