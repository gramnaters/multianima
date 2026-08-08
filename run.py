from flask import Flask, render_template, request, make_response, send_from_directory, Blueprint
from flask_compress import Compress
import logging, os, hashlib, sys, io

# Fix Unicode on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from config import Config

from app.routes.manifest import manifest_bp, MANIFEST
from app.routes.catalog import catalog_bp
from app.routes.meta import meta_bp
from app.routes.stream import stream_bp

app = Flask(__name__, template_folder='./templates', static_folder='./static')
app.config.from_object('config.Config')
app.register_blueprint(manifest_bp)
app.register_blueprint(catalog_bp)
app.register_blueprint(meta_bp)
app.register_blueprint(stream_bp)

Compress(app)
logging.basicConfig(format='%(asctime)s %(message)s')

@app.route('/')
@app.route('/<lang>/')
def index(lang=None):
    return render_template('configure.html')

@app.route('/configure')
@app.route('/<lang>/configure')
def configure(lang=None):
    return render_template('configure.html')

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

@app.route('/.well-known/ai-plugin.json')
@app.route('/health')
def health():
    return {'status': 'ok', 'version': MANIFEST['version']}


if __name__ == '__main__':
    port = int(Config.FLASK_PORT) if Config.FLASK_PORT.isdigit() else 5000
    print(f'Hindi Dub Anime Hub | http://localhost:{port}')
    print(f'Configure: http://localhost:{port}/configure')
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG == 'True')
