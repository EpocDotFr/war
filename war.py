from flask import Flask, render_template, request, abort, json
from flask_httpauth import HTTPBasicAuth
from flask_debugtoolbar import DebugToolbarExtension
from urllib.parse import quote_plus
from bugsnag.handlers import BugsnagHandler
from werkzeug.exceptions import HTTPException
from bugsnag.flask import handle_exceptions
import gauges
import bugsnag
import bugsnag_client
import os


# -----------------------------------------------------------
# Boot


app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

gauges.TOKEN = app.config['GAUGES']['API_TOKEN']
bugsnag_client.API_KEY = app.config['BUGSNAG']['ORG_API_KEY']

if not app.config['DEBUG']:
    bugsnag.configure(api_key=app.config['BUGSNAG']['NOTIFIER_API_KEY'])
    handle_exceptions(app)
    app.logger.addHandler(BugsnagHandler())

auth = HTTPBasicAuth()

debug_toolbar = DebugToolbarExtension(app)

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

from utils import *

# -----------------------------------------------------------
# CLI commands


@app.cli.command()
def initdb():
    """Create the MongoDB collection's goods."""
    db = get_database()

    db.samples.create_index('audio_database')
    db.news.create_index('slug')


@app.cli.command()
def emptydb():
    """Empty the MongoDB database."""
    db = get_database()

    db.samples.delete_many({})
    db.stats.delete_many({})
    db.news.delete_many({})


@app.cli.command()
def resetdb():
    """Drop the MongoDB database."""
    db = get_database()

    db.samples.drop()
    db.stats.drop()
    db.news.drop()


@app.cli.command()
def worker():
    """Start the beanstalkd worker."""
    queue = get_queue()
    queue.watch('samples')

    push = get_push()

    db = get_database()

    app.logger.info('Initialized')

    while True:
        job = queue.reserve()

        app.logger.info('Incomming job')

        job_data = json.loads(job.body)
        sample_id = job_data['sample_id']
        sample_object_id = ObjectId(sample_id)

        sample = db.samples.find_one({'_id': sample_object_id})

        if sample is None:
            raise Exception('The sample {} does not exists in the database'.format(sample_id))

        push_channel = 'results-{}'.format(sample_id)

        audio_databases = get_enabled_audio_databases(db)

        there_were_errors = False

        for audio_database_id, audio_database_instance in audio_databases.items():
            if audio_database_id in sample and sample[audio_database_id] is not None:
                continue

            try:
                recognization = audio_database_instance.recognize(sample_id)

                db.samples.update_one({'_id': sample_object_id}, {'$set': {audio_database_id: recognization}})

                if recognization['status'] == 'success':
                    db.stats.update_one({'audio_database': audio_database_id}, {'$inc': {'successes': 1}})

                    search_terms = []

                    if 'artist' in recognization['data']:
                        search_terms.append(recognization['data']['artist'])

                    if 'title' in recognization['data']:
                        search_terms.append(recognization['data']['title'])

                    recognization['data']['search_terms'] = quote_plus(' '.join(search_terms))

                    push.trigger(push_channel, 'success', {
                        'audio_database_id': audio_database_id,
                        'audio_database_name': audio_database_instance.get_name(),
                        'data': recognization['data']
                    })
                elif recognization['status'] == 'failure':
                    db.stats.update_one({'audio_database': audio_database_id}, {'$inc': {'failures': 1}})

                    push.trigger(push_channel, 'failure', {
                        'audio_database_id': audio_database_id,
                        'audio_database_name': audio_database_instance.get_name()
                    })
                elif recognization['status'] == 'error':
                    there_were_errors = True

                    push.trigger(push_channel, 'error', {
                        'audio_database_id': audio_database_id,
                        'audio_database_name': audio_database_instance.get_name(),
                        'data': recognization['data']
                    })

                    app.logger.error(recognization['data']['message'])

            except Exception as e:
                there_were_errors = True

                db.samples.update_one({'_id': sample_object_id}, {'$set': {audio_database_id: {
                    'status': 'error',
                    'data': {'message': str(e)}
                }}})

                push.trigger(push_channel, 'error', {
                    'audio_database_id': audio_database_id,
                    'audio_database_name': audio_database_instance.get_name(),
                    'data': {'message': str(e)}
                })

                app.logger.error(e)

        db.samples.update_one({'_id': sample_object_id}, {'$set': {'done': True}})
        push.trigger(push_channel, 'done', {})
        job.delete()

        if not there_were_errors:
            app.logger.info('No errors')
            os.remove(get_sample_file_path(sample_id))
        else:
            app.logger.info('There were errors')


# -----------------------------------------------------------
# Hooks

@app.before_request
def define_globals():
    g.INCLUDE_WEB_ANALYTICS = not app.config['DEBUG']
    g.NO_INDEX = False


@app.before_request
def check_under_maintenance():
    if os.path.exists('maintenance') and not request.path.startswith('/manage'):
        abort(503)


@app.before_request
def manage_area():
    if request.path.startswith('/manage'):
        g.INCLUDE_WEB_ANALYTICS = False
        g.NO_INDEX = True


@app.teardown_appcontext
def close_database(error):
    if hasattr(g, 'database'):
        g.database.client.close()


@app.teardown_appcontext
def close_queue(error):
    if hasattr(g, 'queue'):
        g.queue.close()


@auth.get_password
def get_password(username):
    if username in app.config['MONITORING_USERS']:
        return app.config['MONITORING_USERS'].get(username)

    return None


@auth.error_handler
def auth_error():
    return http_error_handler(403, without_code=True)


# -----------------------------------------------------------
# HTTP errors handler


@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(500)
@app.errorhandler(503)
def http_error_handler(error, without_code=False):
    if isinstance(error, HTTPException):
        error = error.code

    g.INCLUDE_WEB_ANALYTICS = False
    g.NO_INDEX = True

    ret = (render_template('errors/{}.html'.format(error)),)

    if not without_code:
        ret = ret + (error,)

    return ret


# -----------------------------------------------------------
# Routes


import routes
