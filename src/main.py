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
    instance_name = data.get('instanceName', 'Desconocido')
    title = data.get('movie', {}).get('title', 'Desconocido')
    release_title = data.get('release', {}).get('releaseTitle', 'Desconocido')
    indexer = data.get('release', {}).get('indexer', 'Desconocido')

    # Eliminar "SPANiSH" al final de release_title (ignorar mayúsculas/minúsculas)
    clean_release_title = re.sub(r'\s*\[?\bSPANiSH\b\]?\s*$', '', release_title, flags=re.IGNORECASE)

    # Definir funciones para cada caso de evento
    def handle_test():
        app.logger.info(f"Conexión de prueba desde {instance_name}")
        return jsonify({"status": "success", "message": f"Conexión de prueba desde {instance_name} exitosa"}), 200

    def handle_grab():
        app.logger.info(f"Release title: {clean_release_title}")
        return jsonify({"status": "success", "message": f"Se ha obtenido una URL para {title} desde {indexer}"}), 200

    # Diccionario que actúa como switch
    event_handlers = {
        "Test": handle_test,
        "Grab": handle_grab,
    }

    # Ejecutar la función correspondiente al evento, si existe
    handler = event_handlers.get(event_type)

    if handler:
        return handler()
    else:
        app.logger.warning(f"Evento no soportado: {event_type}")
        app.logger.info(data)
        return jsonify({"status": "error", "message": "Evento no soportado"}), 400

# Status healthcheck endpoint
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "OK"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
