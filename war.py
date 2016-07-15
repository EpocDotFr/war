from flask import Flask, render_template, jsonify, request, g, abort, flash, json
from logging.handlers import RotatingFileHandler
from bson.objectid import ObjectId
from urllib.parse import quote_plus
import os
import logging
import pymongo

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
# Configuration parameters that cannot be customized via
# the config.py file

app.config['INCLUDE_WEB_ANALYTICS'] = not app.config['DEBUG']
app.config['NO_INDEX'] = False

# -----------------------------------------------------------
# CLI commands

@app.cli.command()
def initdb():
    """Initialize the MongoDB collections"""
    db = get_database()

    db.samples.create_index('audio_database')


@app.cli.command()
def emptydb():
    """Empty the MongoDB collections"""
    db = get_database()

    db.samples.delete_many({})
    db.stats.delete_many({})


@app.cli.command()
def worker():
    """Start a beanstalkd worker"""
    queue = get_queue()
    queue.watch('samples')

    job = queue.reserve()

    try:
        job_data = json.loads(job.body)

        db = get_database()

        audio_databases = get_enabled_audio_databases(db)

        for audio_database_id, audio_database_instance in audio_databases.items():
            try:
                recognization_results = audio_database_instance.recognize(job_data['sample_id'])

                if recognization_results is False:
                    db.stats.update_one({'audio_database': audio_database_id}, {'$inc': {'failures': 1}})
                else:
                    db.samples.update_one({'_id': ObjectId(job_data['sample_id'])}, {'$set': {audio_database_id: recognization_results}})
                    db.stats.update_one({'audio_database': audio_database_id}, {'$inc': {'successes': 1}})
            except Exception as e:
                app.logger.error(str(e))

        db.samples.update_one({'_id': ObjectId(job_data['sample_id'])}, {'$set': {'done': True}})
        job.delete()
    except Exception as e:
        app.logger.error(str(e))
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


# About page
@app.route('/about')
def about():
    return render_template('about.html')


# FAQ page
@app.route('/faq')
def faq():
    return render_template('faq.html')


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


# Monitoring page
@app.route('/monitoring')
def monitoring():
    app.config['INCLUDE_WEB_ANALYTICS'] = False
    app.config['NO_INDEX'] = True

    return render_template('monitoring.html')


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

            db_data = {
                'done': False
            }

            for audio_database_classname in enabled_audio_databases:
                db_data[audio_database_classname] = None

            sample = db.samples.insert_one(db_data)

            sample_id = str(sample.inserted_id)

            recognization_job_data = {'sample_id': sample_id}

            queue = get_queue()
            queue.use('samples')
            queue.put(json.dumps(recognization_job_data))

            sample_file = request.files['sample']
            sample_file_path = get_sample_file_path(sample_id)
            sample_file.save(sample_file_path)
            
            ajax_response['result'] = 'success'
            ajax_response['data']['sample_id'] = sample_id

            flash('Your sample was successfully submitted!', 'success')

            status = 202
        except Exception as e:
            app.logger.error(str(e))
            status = 500
            ajax_response['data']['message'] = 'Sorry, there were a server error. We have been informed about this.'

    return jsonify(ajax_response), status


# Sample results
@app.route('/r/<sample_id>')
def results(sample_id):
    app.config['INCLUDE_WEB_ANALYTICS'] = False
    app.config['NO_INDEX'] = True

    db = get_database()

    sample = db.samples.find_one({'_id': ObjectId(sample_id)})

    if sample is None:
        abort(404)

    results = []

    audio_databases = get_enabled_audio_databases(db)

    for audio_database_id, audio_database_instance in audio_databases.items():
        if audio_database_id in sample and sample[audio_database_id] is not None:
            search_terms = []

            if 'artist' in sample[audio_database_id]:
                search_terms.append(sample[audio_database_id]['artist'])

            if 'title' in sample[audio_database_id]:
                search_terms.append(sample[audio_database_id]['title'])

            results.append({
                'audio_database_id': audio_database_id,
                'audio_database_name': audio_database_instance.get_name(),
                'track': sample[audio_database_id],
                'search_terms': quote_plus(' '.join(search_terms))
            })

    return render_template('results.html', sample=sample, results=results)


# Not Found
@app.errorhandler(404)
def error_404(error):
    return render_template('404.html'), 404


# Internal Server Error
@app.errorhandler(500)
def error_500(error):
    app.logger.error(str(error))
    return render_template('500.html'), 500


# Service Unavailable
@app.errorhandler(503)
def error_503(error):
    return render_template('503.html'), 503


# Unauthorized
@app.errorhandler(401)
def error_401(error):
    return render_template('401.html'), 401


# Forbidden
@app.errorhandler(403)
def error_403(error):
    return render_template('403.html'), 403
