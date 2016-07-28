from flask import Flask,  render_template, request, abort, json
from flask_httpauth import HTTPBasicAuth
from urllib.parse import quote_plus
import gauges
import os
import bugsnag
from bugsnag.flask import handle_exceptions

# -----------------------------------------------------------
# Boot

gauges.TOKEN = app.config['GAUGES_API_TOKEN']

app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

if not app.config['DEBUG']:
    bugsnag.configure(
      api_key = app.config['BUGSNAG_API_KEY']
    )

    handle_exceptions(app)

auth = HTTPBasicAuth()

from utils import *

# -----------------------------------------------------------
# Global per-request config parameters

with app.app_context():
    g.INCLUDE_WEB_ANALYTICS = not app.config['DEBUG']
    g.NO_INDEX = False


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

    job = queue.reserve()

    push = get_push()

    try:
        db = get_database()

        job_data = json.loads(job.body)
        sample_id = job_data['sample_id']
        sample_object_id = ObjectId(sample_id)

        sample = db.samples.find_one({'_id': sample_object_id})

        if sample is None:
            raise Exception('The sample {} does not exists in the database'.format(sample_id))

        push_channel = 'results-{}'.format(sample_id)

        audio_databases = get_enabled_audio_databases(db)

        for audio_database_id, audio_database_instance in audio_databases.items():
            if audio_database_id in sample and sample[audio_database_id] is not None:
                continue

            try:
                recognization_results = audio_database_instance.recognize(sample_id)

                db.samples.update_one({'_id': sample_object_id}, {'$set': {audio_database_id: recognization_results}})

                if not recognization_results:
                    db.stats.update_one({'audio_database': audio_database_id}, {'$inc': {'failures': 1}})

                    push.trigger(push_channel, 'failure', {
                        'audio_database_id': audio_database_id,
                        'audio_database_name': audio_database_instance.get_name()
                    })
                else:
                    db.stats.update_one({'audio_database': audio_database_id}, {'$inc': {'successes': 1}})

                    search_terms = []

                    if 'artist' in recognization_results:
                        search_terms.append(recognization_results['artist'])

                    if 'title' in recognization_results:
                        search_terms.append(recognization_results['title'])

                    push.trigger(push_channel, 'success', {
                        'audio_database_id': audio_database_id,
                        'audio_database_name': audio_database_instance.get_name(),
                        'track': recognization_results,
                        'search_terms': quote_plus(' '.join(search_terms))
                    })
            except Exception as e:
                push.trigger(push_channel, 'error', {
                    'audio_database_id': audio_database_id,
                    'audio_database_name': audio_database_instance.get_name()
                })

                app.logger.error(str(e))

        db.samples.update_one({'_id': sample_object_id}, {'$set': {'done': True}})
        push.trigger(push_channel, 'done', {})
        job.delete()
    except Exception as e:
        app.logger.error(str(e))
        job.bury()


# -----------------------------------------------------------
# Hooks


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
    return render_template('errors/403.html')

import routes