from bson.objectid import ObjectId
from flask import g
from pymongo import MongoClient
from pystalkd import Beanstalkd
from slugify import slugify
from war import app
import sample_store
import arrow
import pusher


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
        'final_result': None,
        'submitted_at': arrow.now().datetime
    }

    enabled_audio_databases = app.config['ENABLED_AUDIO_DATABASES']

    for audio_database_classname in enabled_audio_databases:
        data[audio_database_classname] = None

    return db.samples.insert_one(data)


def delete_one_sample(db, sample_id):
    sample_store.delete_locally(sample_id)

    return db.samples.delete_one({'_id': ObjectId(sample_id)}).deleted_count > 0


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
    else:
        sample['submitted_at'] = None

    if 'file_url' not in sample:
        sample['file_url'] = None

    return sample


def get_one_sample_by_id(db, sample_id):
    sample = db.samples.find_one({'_id': ObjectId(sample_id)})

    return _get_one_sample(sample)


def get_latest_success_samples(db, num=3):
    samples = db.samples.find({
        'done': {'$eq': True},
        'final_result': {'$ne': None},
        'ACRCloud.status': {'$eq': 'success'}, # TODO temporary
    }).limit(num).sort('submitted_at', -1)

    samples_list = []

    for sample in samples:
        sample = _get_one_sample(sample)

        samples_list.append(sample)

    return samples_list


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


def get_enabled_audio_databases(db):
    ret = {}

    enabled_audio_databases = app.config['ENABLED_AUDIO_DATABASES']

    audio_databases_module = __import__('audio_databases')

    for audio_database_classname in enabled_audio_databases:
        audio_database_class = getattr(audio_databases_module, audio_database_classname)
        audio_database_instance = audio_database_class(db)

        ret[audio_database_classname] = audio_database_instance

    return ret
