from flask import g
from war import app
from pymongo import MongoClient
from pystalkd import Beanstalkd
import os
import pusher


def get_database():
    if not hasattr(g, 'database'):
        mongodb_client = MongoClient('mongodb://{}:{}'.format(app.config['MONGODB_HOST'], app.config['MONGODB_PORT']), connectTimeoutMS=3000, serverSelectionTimeoutMS=3000)

        g.database = mongodb_client.war

    return g.database


def get_queue():
    if not hasattr(g, 'queue'):
        g.queue = Beanstalkd.Connection(app.config['BEANSTALKD_HOST'], app.config['BEANSTALKD_PORT'])

    return g.queue


def get_push():
    if not hasattr(g, 'push'):
        g.push = pusher.Pusher(
          app_id=app.config['PUSHER_APP_ID'],
          key=app.config['PUSHER_KEY'],
          secret=app.config['PUSHER_SECRET'],
          cluster=app.config['PUSHER_CLUSTER'],
          ssl=True
        )

    return g.push


def get_global_stats(db):
    global_stats_db = db.stats.aggregate([
        {'$group': {
            '_id': None,
            'total_successes': {'$sum': '$successes'},
            'total_failures': {'$sum': '$failures'}
        }}
    ])

    global_stats = list(global_stats_db)

    if len(global_stats) == 1:
        global_stats = global_stats[0]

        global_stats['total_successes_and_failures'] = global_stats['total_successes'] + global_stats['total_failures']
        global_stats['total_successes_percent'] = 0 if global_stats['total_successes_and_failures'] == 0 else round((global_stats['total_successes'] * 100) / global_stats['total_successes_and_failures'])
        global_stats['total_failures_percent'] = 0 if global_stats['total_successes_and_failures'] == 0 else round((global_stats['total_failures'] * 100) / global_stats['total_successes_and_failures'])

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
        raise Exception('This sample file does not exists ({}.wav)'.format(sample_id))

    return sample_file_path


def get_enabled_audio_databases(db):
    ret = {}

    enabled_audio_databases = app.config['ENABLED_AUDIO_DATABASES']

    audio_databases_module = __import__('audio_databases')

    for audio_database_classname in enabled_audio_databases:
        audio_database_class = getattr(audio_databases_module, audio_database_classname)
        audio_database_instance = audio_database_class(db)

        ret[audio_database_classname] = audio_database_instance

    return ret
