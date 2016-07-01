from flask import Flask, render_template, jsonify, request
from logging.handlers import RotatingFileHandler
import os
import uuid
import logging

# -----------------------------------------------------------
# Boot

app = Flask(__name__)
app.config.from_pyfile('config.py')

# -----------------------------------------------------------
# Logging configuration

logging_handler = RotatingFileHandler(os.path.join(app.config['LOGS_PATH'], 'war.log'), maxBytes=10000, backupCount=2)
logging_handler.setLevel(logging.INFO)
logging_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))

app.logger.addHandler(logging_handler)

from utils import get_sample_file_path, get_enabled_audio_databases

# -----------------------------------------------------------
# Routes

# Home page
@app.route('/')
def home():
    return render_template('home.html')


# FAQ page
@app.route('/faq')
def faq():
    return render_template('faq.html')


# About page
@app.route('/about')
def about():
    return render_template('about.html')


# Stats page
@app.route('/stats')
def stats():
    audio_databases = get_enabled_audio_databases()

    return render_template('stats.html', audio_databases=audio_databases)


# Sample recognization handling
@app.route('/recognize', methods=['POST'])
def recognize():
    result = {
        'result': 'failure',
        'data': {}
    }
    
    app.logger.info('New request')

    if not request.is_xhr or 'sample' not in request.files or request.files['sample'] == '':
        app.logger.error('Invalid request')
        status = 400
        result['data']['message'] = 'Invalid request'
    else:
        try:
            sample_file = request.files['sample']

            sample_file_uuid = uuid.uuid4()
            
            sample_file_path = get_sample_file_path(sample_file_uuid)
            
            app.logger.info('Saving sample file to {}'.format(sample_file_path))

            sample_file.save(sample_file_path)
            
            result['result'] = 'success'
            result['data']['uuid'] = sample_file_uuid

            status = 202
        except Exception as e:
            app.logger.error(e)
            status = 500
            result['data']['message'] = 'Oops, there were a server error.'

    return jsonify(result), status


# Not Found
@app.errorhandler(404)
def error_404(error):
    return render_template('404.html')


# Internal Server Error
@app.errorhandler(500)
def error_500(error):
    app.logger.error(error)
    return render_template('500.html')


# Service Unavailable
@app.errorhandler(503)
def error_503(error):
    return render_template('503.html')
