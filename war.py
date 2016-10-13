from flask import Flask, render_template, request, abort, json
from flask_httpauth import HTTPBasicAuth
from flask_misaka import Misaka
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
from werkzeug.exceptions import HTTPException
import gauges
import os
import uuid


# -----------------------------------------------------------
# Boot


app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

gauges.TOKEN = app.config['GAUGES']['API_TOKEN']

if not app.config['DEBUG']:
    from bugsnag.handlers import BugsnagHandler
    from bugsnag.flask import handle_exceptions
    import bugsnag
    import bugsnag_client

    bugsnag_client.API_KEY = app.config['BUGSNAG']['ORG_API_KEY']

    bugsnag.configure(api_key=app.config['BUGSNAG']['NOTIFIER_API_KEY'])
    handle_exceptions(app)
    app.logger.addHandler(BugsnagHandler())
else:
    import logging
    from logging.handlers import RotatingFileHandler

    formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    handler = RotatingFileHandler(os.path.join(app.config['LOGS_PATH'], 'app.log'), maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

auth = HTTPBasicAuth()

db = SQLAlchemy(app)

Misaka(app)

import sample_store
from utils import *
from models import *

# -----------------------------------------------------------
# CLI commands


@app.cli.command()
def create_database():
    """Delete then create all the database tables."""

    db.drop_all()
    db.create_all()


@app.cli.command()
def base_seed_database():
    """Seeds the database with base data."""

    audio_databases = [
        {'name': 'ACRCloud', 'class_name': 'ACRCloud', 'website': 'https://www.acrcloud.com/', 'is_enabled': True},
        {'name': 'Gracenote', 'class_name': 'Gracenote', 'website': 'http://www.gracenote.com/', 'is_enabled': False},
        {'name': 'Audible Magic', 'class_name': 'AudibleMagic', 'website': 'http://www.audiblemagic.com/', 'is_enabled': False},
        {'name': 'Mufin AudioID', 'class_name': 'MufinAudioID', 'website': 'https://www.mufin.com/', 'is_enabled': False},
        {'name': 'AcoustID', 'class_name': 'AcoustID', 'website': 'https://acoustid.org/', 'is_enabled': False},
    ]

    for one_audio_database in audio_databases:
        db.session.add(AudioDatabase(
            name=one_audio_database['name'],
            class_name=one_audio_database['class_name'],
            website=one_audio_database['website'],
            is_enabled=one_audio_database['is_enabled']
        ))

    db.session.commit()


@app.cli.command()
def fake_seed_database():
    """Seeds the database with fake data."""

    fake_news = [
        {'slug': 'ahah-ahah-ah', 'title': 'Ahah ahah AH', 'date': arrow.get('2016-10-12 18:00:00').datetime, 'content': '*Some* _fucking_ [markdown](https://epoc.fr)', 'tags': 'gtfo'},
        {'slug': 'blah-blah', 'title': 'Blah blah', 'date': arrow.get('2016-10-11 15:45:00').datetime, 'content': '*Some* _fucking_ [markdown](https://epoc.fr)', 'tags': 'hey'},
        {'slug': 'this-is-a-test-draft', 'title': 'THIS is a test draft!', 'date': None, 'content': '*Some* _fucking_ [markdown](https://epoc.fr)', 'tags': ''},
        {'slug': 'one-more', 'title': 'One more', 'date': arrow.get('2016-10-09 10:30:00').datetime, 'content': '*Some* _fucking_ [markdown](https://epoc.fr)', 'tags': 'gtfo,hey'}
    ]

    for one_fake_news in fake_news:
        db.session.add(News(
            slug=one_fake_news['slug'],
            title=one_fake_news['title'],
            date=one_fake_news['date'],
            content=one_fake_news['content'],
            tags=one_fake_news['tags']
        ))

    db.session.commit()

    fake_samples = [
        {'uuid': str(uuid.uuid4()).replace('-', ''), 'submitted_at': arrow.get('2016-10-13 13:30:00').datetime, 'done_at': None, 'wav_file_url': 'http://www.kozco.com/tech/piano2.wav'},
        {'uuid': str(uuid.uuid4()).replace('-', ''), 'submitted_at': arrow.get('2016-10-12 11:30:00').datetime, 'done_at': None, 'wav_file_url': 'http://www.kozco.com/tech/piano2.wav'},
        {'uuid': str(uuid.uuid4()).replace('-', ''), 'submitted_at': arrow.get('2016-10-26 22:20:00').datetime, 'done_at': arrow.get('2016-10-13 16:40:30').datetime, 'wav_file_url': 'http://www.kozco.com/tech/piano2.wav'},
        {'uuid': str(uuid.uuid4()).replace('-', ''), 'submitted_at': arrow.get('2016-10-06 18:10:00').datetime, 'done_at': None, 'wav_file_url': None}
    ]

    ACRCloud = AudioDatabase.query.filter_by(class_name = 'ACRCloud').first()

    for one_fake_sample in fake_samples:
        fake_sample = Sample(
            uuid=one_fake_sample['uuid'],
            submitted_at=one_fake_sample['submitted_at'],
            done_at=one_fake_sample['done_at'],
            wav_file_url=one_fake_sample['wav_file_url']
        )

        db.session.add(fake_sample)
        db.session.flush()

        db.session.add(RecognitionResult(
            is_final=True,
            status=RecognitionResultStatus.success,
            sample=fake_sample,
            audio_database=ACRCloud,
            artist='AC/DC',
            title='Hells Bells'
        ))

    db.session.commit()


@app.cli.command()
def migrate_database():
    """Migrate the data from MongoDB to the SQL database."""

    mongo = get_database()

    mongo_news = get_news_list(mongo, admin=True)

    for one_mongo_news in mongo_news:
        db.session.add(News(
            slug=one_mongo_news['slug'],
            title=one_mongo_news['title'],
            date=one_mongo_news['date'].datetime if 'date' in one_mongo_news and one_mongo_news['date'] is not None else None,
            content=one_mongo_news['content'],
            tags=','.join(one_mongo_news['tags']) if 'tags' in one_mongo_news and one_mongo_news['tags'] is not None else None
        ))

    db.session.commit()

    mongo_samples = mongo.samples.find()

    ACRCloud = AudioDatabase.query.filter_by(class_name='ACRCloud').first()

    for mongo_sample in mongo_samples:
        mongo_sample = get_one_sample(mongo_sample)

        sql_sample = Sample(
            uuid=str(mongo_sample['_id']),
            submitted_at=mongo_sample['submitted_at'].datetime,
            done_at=mongo_sample['submitted_at'].replace(minutes=+1).datetime if mongo_sample['done'] else None,
            wav_file_url=mongo_sample['file_url'] if 'file_url' in mongo_sample else None
        )

        db.session.add(sql_sample)
        db.session.flush()

        if 'ACRCloud' in mongo_sample and mongo_sample['ACRCloud'] is not None:
            audio_db = mongo_sample['ACRCloud']

            if audio_db['status'] == 'success':
                status = RecognitionResultStatus.success
            elif audio_db['status'] == 'error':
                status = RecognitionResultStatus.error
            elif audio_db['status'] == 'failure':
                status = RecognitionResultStatus.failure

            db.session.add(RecognitionResult(
                is_final=True,
                status=status,
                sample=sql_sample,
                audio_database=ACRCloud,
                artist=audio_db['data']['artist'] if 'artist' in audio_db['data'] else None,
                title=audio_db['data']['title'] if 'title' in audio_db['data'] else None,
                infos=audio_db['data']['message'] if 'message' in audio_db['data'] else None
            ))

    db.session.commit()


@app.cli.command()
def samples_recognize():
    """Samples recognization worker."""
    queue = get_queue()
    queue.watch('war-samples-recognize')

    push = get_push()

    db = get_database()

    app.logger.info('Initialized')

    # For each beanstalk jobs
    while True:
        job = queue.reserve()

        if not job:
            app.logger.error('Unable to reserve job')
            continue

        try:
            job_data = json.loads(job.body)
        except Exception as e:
            job.delete()
            app.logger.error(e)
            continue

        sample_id = job_data['sample_id']

        # Get the sample in the database
        sample = get_one_sample_by_id(db, sample_id)

        if sample is None:
            job.delete()
            app.logger.error('The sample {} does not exists in the database'.format(sample_id))
            continue

        # Pusher channel where updates will be pushed
        push_channel = 'results-{}'.format(sample_id)

        sample_file_path = sample_store.get_local_path(sample_id)

        # Upload the sample to the object storage if it's not already done
        if sample['file_url'] is None and os.path.exists(sample_file_path):
            try:
                with open(sample_file_path, 'rb') as sample_file:
                    sample_store.save_remotely(sample_file, sample_id)

                sample_file_url = sample_store.get_remote_path(sample_id)

                update_one_sample(db, sample_id, {'$set': {'file_url': sample_file_url}})
                sample['file_url'] = sample_file_url

                push.trigger(push_channel, 'can-play', {'file_url': sample_file_url})
            except Exception as e:
                app.logger.error(e)
        elif not os.path.exists(sample_file_path) and sample['file_url']:
            try:
                sample_store.download_from_remote(sample_id)
            except Exception as e:
                job.delete()
                app.logger.error(e)
                continue
        elif os.path.exists(sample_file_path) and sample['file_url']:
            # Do nothing
            pass
        else:
            job.delete()
            app.logger.error('The sample {} doesn\'t have file to recognize at all'.format(sample_id))
            continue

        audio_databases = get_enabled_audio_databases(db)

        there_were_errors = False

        # For each enabled audio database
        for audio_database_id, audio_database_instance in audio_databases.items():
            if audio_database_id not in sample:
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
            sample_store.delete_locally(sample_id)
        else:
            app.logger.info('There were errors')


# -----------------------------------------------------------
# Hooks

@app.before_request
def define_globals():
    g.INCLUDE_WEB_ANALYTICS = not app.config['DEBUG']
    g.NO_INDEX = False
    g.SHOW_MANAGE_BAR = False


@app.before_request
def check_under_maintenance():
    if os.path.exists('maintenance') and not request.path.startswith('/manage'):
        abort(503)


@app.before_request
def manage_area():
    if request.path.startswith('/manage'):
        g.INCLUDE_WEB_ANALYTICS = False
        g.NO_INDEX = True


@app.before_request
def show_manage_bar():
    if auth.username() != '' and auth.username() != None:
        g.SHOW_MANAGE_BAR = True


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
    else:
        error = 500

    g.INCLUDE_WEB_ANALYTICS = False
    g.NO_INDEX = True

    ret = (render_template('errors/{}.html'.format(error)),)

    if not without_code:
        ret = ret + (error,)

    return ret


# -----------------------------------------------------------
# Routes


import routes
