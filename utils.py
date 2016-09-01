from flask import g
from war import app
from pymongo import MongoClient
from pystalkd import Beanstalkd
from bson.objectid import ObjectId
from slugify import slugify
import os
import pusher
import arrow


def get_database():
    if not hasattr(g, 'database'):
        mongodb_client = MongoClient('mongodb://{}:{}'.format(app.config['MONGODB']['HOST'], app.config['MONGODB']['PORT']),
                                     connectTimeoutMS=3000, serverSelectionTimeoutMS=3000)

        g.database = mongodb_client.war

    return g.database


def get_queue():
    if not hasattr(g, 'queue'):
        g.queue = Beanstalkd.Connection(app.config['BEANSTALKD']['HOST'], app.config['BEANSTALKD']['PORT'])

    return g.queue


def get_push():
    if not hasattr(g, 'push'):
        g.push = pusher.Pusher(
            app_id=app.config['PUSHER']['APP_ID'],
            key=app.config['PUSHER']['KEY'],
            secret=app.config['PUSHER']['SECRET'],
            cluster=app.config['PUSHER']['CLUSTER'],
            ssl=True
        )

    return g.push


def get_latest_news(db):
    latest_news = db.news.find({'date': {'$ne': None, '$lte': arrow.now().datetime}}).limit(1).sort('date', -1)

    latest_news = list(latest_news)

    if len(latest_news) == 1:
        latest_news = latest_news[0]

        latest_news['date'] = arrow.get(latest_news['date'])

        return latest_news
    else:
        return None


def get_news_list(db, limit=None, admin=False):
    params = {}

    if not admin:
        params = {'date': {'$ne': None, '$lte': arrow.now().datetime}}

    news_list_db = db.news.find(params).sort('date', -1)

    if limit is not None:
        news_list_db = news_list_db.limit(limit)

    news_list = []

    for the_news in news_list_db:
        news_list.append(_get_one_news(the_news))

    return news_list


def _get_one_news(the_news=None):
    if the_news is None:
        return None

    the_news = dict(the_news)

    if the_news['date'] is not None:
        the_news['date'] = arrow.get(the_news['date'])

    return the_news


def get_one_news_by_slug(db, slug):
    the_news = db.news.find_one({'slug': slug})

    return _get_one_news(the_news)


def get_one_news_by_id(db, news_id):
    the_news = db.news.find_one({'_id': ObjectId(news_id)})

    return _get_one_news(the_news)


def update_one_news(db, news_id, title, content, date=None):
    data = {
        'title': title,
        'slug': slugify(title),
        'content': content
    }

    if date is not None:
        data['date'] = arrow.get(date).datetime
    else:
        data['date'] = None

    return db.news.update_one(
        {'_id': ObjectId(news_id)},
        {'$set': data}
    ).modified_count > 0


def create_one_news(db, title, content, date=None):
    data = {
        'title': title,
        'slug': slugify(title),
        'content': content
    }

    if date is not None:
        data['date'] = arrow.get(date).datetime
    else:
        data['date'] = None

    return db.news.insert_one(data)


def delete_one_news(db, news_id):
    return db.news.delete_one({'_id': ObjectId(news_id)}).deleted_count > 0


def create_one_sample(db):
    data = {
        'done': False,
        'submitted_at': arrow.now().datetime
    }

    enabled_audio_databases = app.config['ENABLED_AUDIO_DATABASES']

    for audio_database_classname in enabled_audio_databases:
        data[audio_database_classname] = None

    return db.samples.insert_one(data)


def update_one_sample(db, sample_id, query):
    return db.samples.update_one(
        {'_id': ObjectId(sample_id)},
        query
    ).modified_count > 0


def _get_one_sample(sample):
    if sample is None:
        return None

    sample = dict(sample)

    if 'submitted_at' in sample and sample['submitted_at'] is not None:
        sample['submitted_at'] = arrow.get(sample['submitted_at'])

    return sample


def get_one_sample_by_id(db, sample_id):
    sample = db.samples.find_one({'_id': ObjectId(sample_id)})

    return _get_one_sample(sample)


def get_five_latest_samples(db):
    samples = db.samples.find({
        'done': {'$eq': True},
        'final_result': {'$ne': None}
    }).limit(5).sort('submitted_at', -1)

    ret = []

    for sample in samples:
        sample = _get_one_sample(sample)

        ret.append('{} - {} ({})'.format(
            sample[sample['final_result']]['artist'],
            sample[sample['final_result']]['title'],
            sample['submitted_at'].humanize()
        ))

    return ' • '.join(ret)


def get_global_stats(db):
    global_stats = db.stats.aggregate([
        {'$group': {
            '_id': None,
            'total_successes': {'$sum': '$successes'},
            'total_failures': {'$sum': '$failures'}
        }}
    ])

    global_stats = list(global_stats)

    if len(global_stats) == 1:
        global_stats = global_stats[0]

        global_stats['total_successes_and_failures'] = global_stats['total_successes'] + global_stats['total_failures']
        global_stats['total_successes_percent'] = 0 if global_stats['total_successes_and_failures'] == 0 else round(
            (global_stats['total_successes'] * 100) / global_stats['total_successes_and_failures'])
        global_stats['total_failures_percent'] = 0 if global_stats['total_successes_and_failures'] == 0 else round(
            (global_stats['total_failures'] * 100) / global_stats['total_successes_and_failures'])

        return global_stats

    return {
        'total_successes': 0,
        'total_failures': 0,
        'total_successes_and_failures': 0,
        'total_successes_percent': 0,
        'total_failures_percent': 0
    }


def get_sample_file_path(sample_id, check_if_exists=False):
    sample_file_destination = os.path.abspath(app.config['SAMPLES_PATH'])
    sample_file_name = '{}.wav'.format(sample_id)
    sample_file_path = os.path.join(sample_file_destination, sample_file_name)

    if check_if_exists and not os.path.exists(sample_file_path):
        raise Exception('The sample file "{}" does not exists on the file system'.format(sample_file_path))

    return sample_file_path

def get_public_sample_file_url(sample_id):
    return '/samples/{}.wav'.format(sample_id)


def get_enabled_audio_databases(db):
    ret = {}

    enabled_audio_databases = app.config['ENABLED_AUDIO_DATABASES']

    audio_databases_module = __import__('audio_databases')

    for audio_database_classname in enabled_audio_databases:
        audio_database_class = getattr(audio_databases_module, audio_database_classname)
        audio_database_instance = audio_database_class(db)

        ret[audio_database_classname] = audio_database_instance

    return ret
