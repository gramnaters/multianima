import json, logging, random
from flask import make_response

def respond_with(data, cache_seconds=600):
    response = make_response(json.dumps(data), 200)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.cache_control.max_age = cache_seconds
    response.cache_control.public = True
    return response

def get_random_agent():
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    ]
    return random.choice(agents)

def log_error(e):
    logging.error(f'Error: {e}', exc_info=True)
