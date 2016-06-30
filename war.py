from flask import Flask, render_template, jsonify, request
from logging.handlers import RotatingFileHandler
from acrcloud.recognizer import ACRCloudRecognizer
import os
import uuid
import logging
import json


app = Flask(__name__)
app.config.from_pyfile('config.py')

logging_handler = RotatingFileHandler(os.path.join(app.config['LOGS_PATH'], 'war.log'), maxBytes=10000, backupCount=2)
logging_handler.setLevel(logging.INFO)
logging_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))

app.logger.addHandler(logging_handler)


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
    return render_template('stats.html')


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

            # -----------------------------------------------------
            # TODO everything after this line is temporary

            # ACRCloud tests

            config = {
                    'host': 'eu-west-1.api.acrcloud.com',
                    'access_key': '572705ff4cb98dd76eede63c7a72d825',
                    'access_secret': 'vwagGtTe062U3XgqkRhV1Se9FJIC369Wu2Sibb8F',
                    'debug': False,
                    'timeout': 10
            }

            acrcloud = ACRCloudRecognizer(config)

            sample_file_path = get_sample_file_path(sample_file_uuid)

            result['data']['recognize_results'] = json.loads(acrcloud.recognize_by_file(sample_file_path, 0))

            # TODO end temporary
            # -----------------------------------------------------

            status = 202
        except Exception as e:
            app.logger.error(e)
            status = 500
            result['data']['message'] = str(e)

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


# TODO put all functions bellow in a module


def get_sample_file_path(sample_file_uuid):
    sample_file_destination = os.path.abspath(app.config['SAMPLES_PATH'])
    sample_file_name = '{}.wav'.format(sample_file_uuid)
    sample_file_path = os.path.join(sample_file_destination, sample_file_name)

    return sample_file_path


def recognize(sample_file_uuid):
    sample_file_path = get_sample_file_path(sample_file_uuid)

    if not os.path.exists(sample_file_path):
        raise Exception('The sample file does not exists')
    
    app.logger.info('Fingerprinting {}'.format(sample_file_path))
    
    # FIXME no more used
    # fingerprint = acoustid.fingerprint_file(sample_file_path)
    
    # app.logger.info('Result: {}'.format(fingerprint[1]))
    # app.logger.info('Sending match request to AcoustID')
    
    # lookup_results = acoustid.lookup(app.config['ACOUSTID_API_KEY'], fingerprint[1], fingerprint[0])
    
    # if not lookup_results['status'] or lookup_results['status'] != 'ok':
    #     raise Exception(lookup_results['message'])
    
    # return lookup_results['results']
