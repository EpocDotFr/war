from flask import Flask, Response, render_template, jsonify, request, abort, json, url_for
from flask_httpauth import HTTPBasicAuth
from logging.handlers import RotatingFileHandler
from bson.objectid import ObjectId
from urllib.parse import quote_plus
import gauges
import os
import logging
import PyRSS2Gen
import psutil

# -----------------------------------------------------------
# Boot

app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')
auth = HTTPBasicAuth()

gauges.TOKEN = app.config['GAUGES_API_TOKEN']

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
    """Drop then create the MongoDB database."""
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
    return render_template('403.html')


# -----------------------------------------------------------
# Routes


# Home page
@app.route('/')
def home():
    db = get_database()

    global_stats = get_global_stats(db)

    latest_news = None

    if app.config['DEBUG']:
        latest_news = get_latest_news(db)

    return render_template('home.html', global_stats=global_stats, latest_news=latest_news)


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


# News list
@app.route('/news')
def news():
    db = get_database()

    news_list = get_news_list(db)

    return render_template('news.html', news_list=news_list)


# RSS of the news
@app.route('/news/rss')
def news_rss():
    db = get_database()

    news_list = get_news_list(db, limit=5)

    rss_items = []

    for the_news in news_list:
        rss_items.append(PyRSS2Gen.RSSItem(
            title=the_news['title'],
            link=url_for('one_news', slug=the_news['slug'], _external=True),
            description=the_news['content'],
            guid=PyRSS2Gen.Guid(url_for('one_news', slug=the_news['slug'], _external=True)),
            pubDate=the_news['date'].datetime
        ))

    rss = PyRSS2Gen.RSS2(
        title='Latest news from WAR (Web Audio Recognizer)',
        link=url_for('home', _external=True),
        description='Latest news from WAR (Web Audio Recognizer)',
        language='en',
        image=PyRSS2Gen.Image(url_for('static', filename='images/logo_128.png'), 'Logo of WAR', url_for('home', _external=True)),
        lastBuildDate=arrow.now().datetime,
        items=rss_items
    )

    return Response(rss.to_xml(encoding='utf-8'), mimetype='application/rss+xml')


# One news
@app.route('/news/<slug>')
def one_news(slug):
    db = get_database()

    the_news = get_one_news(db, slug)

    if the_news is None:
        abort(404)

    return render_template('one_news.html', the_news=the_news)


# Managing dashboard
@app.route('/manage')
@auth.login_required
def manage():
    db = get_database()

    app.config['INCLUDE_WEB_ANALYTICS'] = False
    app.config['NO_INDEX'] = True

    visits = gauges.get_gauge(app.config['GAUGES_SITE_ID'])

    server = {
        'cpu': psutil.cpu_percent(interval=1),
        'ram': psutil.virtual_memory().percent,
        'hdd': psutil.disk_usage('/').percent
    }

    news_list = get_news_list(db)

    return render_template('manage.html', visits=visits, server=server, news_list=news_list)


# Sample recognization handling
@app.route('/recognize', methods=['POST'])
def recognize():
    ajax_response = {
        'result': 'failure',
        'data': {}
    }

    if not request.is_xhr or 'sample' not in request.files:
        app.logger.warning('Invalid request')
        status = 400
        ajax_response['data']['message'] = 'Invalid request'
    else:
        sample_file = request.files['sample']

        if not is_sample_valid(sample_file):
            app.logger.warning('Invalid sample file')
            status = 400
            ajax_response['data']['message'] = 'Invalid sample file'
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

                sample_file_path = get_sample_file_path(sample_id)
                sample_file.save(sample_file_path)

                ajax_response['result'] = 'success'
                ajax_response['data']['sample_id'] = sample_id

                status = 202
            except Exception as e:
                app.logger.error(str(e))
                status = 500
                ajax_response['data']['message'] = 'Sorry, there were a server error. We have been informed about this.'

    return jsonify(ajax_response), status


# Sample results
@app.route('/r/<sample_id>')
def results(sample_id):
    app.config['NO_INDEX'] = True

    db = get_database()

    sample = db.samples.find_one({'_id': ObjectId(sample_id)})

    if sample is None:
        abort(404)

    res = []

    audio_databases = get_enabled_audio_databases(db)

    for audio_database_id, audio_database_instance in audio_databases.items():
        if audio_database_id in sample and sample[audio_database_id] is not None:
            if sample[audio_database_id] is False:
                res.append({
                    'audio_database_id': audio_database_id,
                    'audio_database_name': audio_database_instance.get_name()
                })
            else:
                search_terms = []

                if 'artist' in sample[audio_database_id]:
                    search_terms.append(sample[audio_database_id]['artist'])

                if 'title' in sample[audio_database_id]:
                    search_terms.append(sample[audio_database_id]['title'])

                    res.append({
                        'audio_database_id': audio_database_id,
                        'audio_database_name': audio_database_instance.get_name(),
                        'track': sample[audio_database_id],
                        'search_terms': quote_plus(' '.join(search_terms))
                    })

    return render_template('results.html', sample=sample, results=res)


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
