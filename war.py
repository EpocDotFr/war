from flask import Flask, render_template, request, abort, json
from flask_httpauth import HTTPBasicAuth
from flask.ext.misaka import Misaka
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
Misaka(app)

gauges.TOKEN = app.config['GAUGES']['API_TOKEN']
bugsnag_client.API_KEY = app.config['BUGSNAG']['ORG_API_KEY']

if not app.config['DEBUG']:
    bugsnag.configure(api_key=app.config['BUGSNAG']['NOTIFIER_API_KEY'])
    handle_exceptions(app)
    app.logger.addHandler(BugsnagHandler())

auth = HTTPBasicAuth()

import sample_store
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
    queue.watch('war-samples-recognize')

    push = get_push()

    db = get_database()

    app.logger.info('Initialized')

    # For each beanstalk jobs
    while True:
        job = queue.reserve()

        app.logger.info('Incomming job')

        job_data = json.loads(job.body)
        sample_id = job_data['sample_id']

        # Get the sample in the database
        sample = get_one_sample_by_id(db, sample_id)

        if sample is None:
            raise Exception('The sample {} does not exists in the database'.format(sample_id))

        push_channel = 'results-{}'.format(sample_id)

        audio_databases = get_enabled_audio_databases(db)

        there_were_errors = False

        # For each enabled audio database
        for audio_database_id, audio_database_instance in audio_databases.items():
            if audio_database_id in sample and sample[audio_database_id] is not None:
                continue

            # Launch recognization process
            try:
                recognization = audio_database_instance.recognize(sample_id)

                update_one_sample(db, sample_id, {'$set': {audio_database_id: recognization}})
                sample[audio_database_id] = recognization

                if recognization['status'] == 'success': # The audio database have found a matching
                    db.stats.update_one({'audio_database': audio_database_id}, {'$inc': {'successes': 1}})

                    search_terms = []

                    if 'artist' in recognization['data']:
                        search_terms.append(recognization['data']['artist'])

                    if 'title' in recognization['data']:
                        search_terms.append(recognization['data']['title'])

                    recognization['data']['search_terms'] = quote_plus(' '.join(search_terms))
                elif recognization['status'] == 'failure': # The audio database doesn't found anything
                    db.stats.update_one({'audio_database': audio_database_id}, {'$inc': {'failures': 1}})
                elif recognization['status'] == 'error': # There were an error with the audio database
                    there_were_errors = True

                    app.logger.error(recognization['data']['message'])

            except Exception as e:
                there_were_errors = True

                update_one_sample(db, sample_id, {
                    '$set': {audio_database_id: {
                        'status': 'error',
                        'data': {'message': str(e)}
                    }}
                })

                sample[audio_database_id] = {
                    'status': 'error',
                    'data': {'message': str(e)}
                }

                app.logger.error(e)

        # TODO
        # Here we'll normally make some fuzzy string matching between all results to set the final
        # recognized result. But as we only have one audio database to search in, we'll force the final
        # result to be the one returned by our only audio database.

        update_one_sample(db, sample_id, {'$set': {'done': True, 'final_result': 'ACRCloud'}})
        sample['done'] = True
        sample['final_result'] = 'ACRCloud'

        if sample[sample['final_result']]['status'] == 'success':
            push.trigger(push_channel, 'success', sample[sample['final_result']]['data'])
        elif sample[sample['final_result']]['status'] == 'failure':
            push.trigger(push_channel, 'failure', {})
        elif sample[sample['final_result']]['status'] == 'error':
            push.trigger(push_channel, 'error', sample[sample['final_result']]['data'])

        # End TODO

        job.delete()

        if not there_were_errors:
            app.logger.info('No errors')
            sample_store.delete_locally(sample_id)
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
