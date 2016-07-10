from flask import Flask, render_template, jsonify, request
from logging.handlers import RotatingFileHandler
import os
import logging
import json

# -----------------------------------------------------------
# Boot

app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

# -----------------------------------------------------------
# Logging configuration

logging_handler = RotatingFileHandler(os.path.join(app.config['LOGS_PATH'], 'war.log'), maxBytes=10000, backupCount=2)
logging_handler.setLevel(logging.INFO)
logging_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))

app.logger.addHandler(logging_handler)

from utils import *


# -----------------------------------------------------------
# CLI commands

@app.cli.command()
def worker():
    queue = get_queue()
    queue.watch('recognizations')

    job = queue.reserve()

    try:
        job_data = json.loads(job.body)

        db = get_database()

        audio_databases = get_enabled_audio_databases(db)

        for audio_database_id, audio_database_instance in audio_databases.items():
            recognization_results = audio_database_instance.recognize(job_data['sample_id'])

            # TODO proper error handling
            db.recognizations.update_one({"_id": job_data['sample_id']}, {audio_database_id: recognization_results})

        job.delete()
    except Exception as e:
        app.logger.warning(str(e))
        job.bury()


# -----------------------------------------------------------
# Hooks


@app.teardown_appcontext
def close_database(error):
    if hasattr(g, 'database'):
        g.database.client.close()


@app.teardown_appcontext
def close_queue(error):
    if hasattr(g, 'queue'):
        g.queue.close()


# -----------------------------------------------------------
# Routes

# Home page
@app.route('/')
def home():
    db = get_database()

    global_stats = get_global_stats(db)

    return render_template('home.html', global_stats=global_stats)


# FAQ page
@app.route('/faq')
def faq():
    return render_template('faq.html')


# About page
@app.route('/about')
def about():
    return render_template('about.html')


# Terms of service page
@app.route('/tos')
def tos():
    return render_template('tos.html')


# Stats page
@app.route('/stats')
def stats():
    db = get_database()

    audio_databases = get_enabled_audio_databases(db)
    global_stats = get_global_stats(db)

    return render_template('stats.html', audio_databases=audio_databases, global_stats=global_stats)


# Sample recognization handling
@app.route('/recognize', methods=['POST'])
def recognize():
    ajax_response = {
        'result': 'failure',
        'data': {}
    }
    
    if not request.is_xhr or 'sample' not in request.files or request.files['sample'] == '':
        app.logger.warning('Invalid request')
        status = 400
        ajax_response['data']['message'] = 'Invalid request'
    else:
        try:
            db = get_database()

            enabled_audio_databases = app.config['ENABLED_AUDIO_DATABASES']

            db_data = {}

            for audio_database_classname in enabled_audio_databases:
                db_data[audio_database_classname] = None

            inserted = db.recognizations.insert_one(db_data)

            sample_id = str(inserted.inserted_id)

            recognization_job_data = {'sample_id': sample_id}

            queue = get_queue()
            queue.use('recognizations')
            queue.put(json.dumps(recognization_job_data))

            sample_file = request.files['sample']
            sample_file_path = get_sample_file_path(sample_id)
            sample_file.save(sample_file_path)
            
            ajax_response['result'] = 'success'
            ajax_response['data']['sample_id'] = sample_id

            status = 202
        except Exception as e:
            app.logger.error(e)
            status = 500
            ajax_response['data']['message'] = 'Sorry, there were a server error. We have been informed about this.'

    return jsonify(ajax_response), status


# Not Found
@app.errorhandler(404)
def error_404(error):
    return render_template('404.html'), 404


# Internal Server Error
@app.errorhandler(500)
def error_500(error):
    app.logger.error(error)
    return render_template('500.html'), 500


# Service Unavailable
@app.errorhandler(503)
def error_503(error):
    return render_template('503.html'), 503
