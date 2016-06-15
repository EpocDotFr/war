from flask import Flask, render_template, jsonify, request, abort
from logging.handlers import RotatingFileHandler
import os
import uuid
import acoustid
import logging


app = Flask(__name__)
app.config.from_pyfile('config.py')

logging_handler = RotatingFileHandler(os.path.join(app.config['LOGS_PATH'], 'war.log'), maxBytes=10000, backupCount=2)
logging_handler.setLevel(logging.INFO)
logging_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))

app.logger.addHandler(logging_handler)


# Home page with the Recognize button
@app.route('/')
def home():
    return render_template('home.html')


# Receive and handle the sample WAV file via AJAX upload
@app.route('/sample', methods=['POST'])
def sample():
    result = {
        'result': 'failure',
        'data': {}
    }
    
    app.logger.info('New request')

    if not request.is_xhr or not request.files['file']:
        app.logger.error('Not an Ajax request or no sample')
        result['data']['message'] = 'Invalid request'

    try:
        sample_file = request.files['file']

        sample_file_uuid = uuid.uuid4()
        
        sample_file_path = get_sample_file_path(sample_file_uuid)
        
        app.logger.info('Saving sample file to {}'.format(sample_file_path))

        sample_file.save(sample_file_path)
        
        result['result'] = 'success'
        result['data']['uuid'] = sample_file_uuid

        # TODO everything after this line is temporary

        recognize_results = recognize(sample_file_uuid)
        
        result['data']['recognize_results'] = recognize_results

        # TODO end temporary
    except Exception as e:
        app.logger.error(e)
        result['data']['message'] = str(e)

    return jsonify(result)


# Not Found
@app.errorhandler(404)
def error_404(error):
    app.logger.warning(error)
    return render_template('404.html', error=error)


# Internal Server Error
@app.errorhandler(500)
def error_500(error):
    app.logger.error(error)
    return render_template('500.html', error=error)

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
    
    fingerprint = acoustid.fingerprint_file(sample_file_path)
    
    app.logger.info('Result: {}'.format(fingerprint[1]))
    app.logger.info('Sending match request to AcoustID');
    
    lookup_results = acoustid.lookup(app.config['ACOUSTID_API_KEY'], fingerprint[1], fingerprint[0])
    
    if not lookup_results['status'] or lookup_results['status'] != 'ok':
        raise Exception(lookup_results['message'])
    
    return lookup_results['results']
