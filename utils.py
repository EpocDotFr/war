from war import app
from pymongo import MongoClient
from beanstalk import serverconn
import os


def get_db():
    mongodb_host = app.config['MONGODB_HOST']
    mongodb_port = app.config['MONGODB_PORT']

    mongodb_client = MongoClient('mongodb://{}:{}'.format(mongodb_host, mongodb_port))

    return mongodb_client.war


def get_queue():
    beanstalkd_host = app.config['BEANSTALKD_HOST']
    beanstalkd_port = app.config['BEANSTALKD_PORT']

    return serverconn.ServerConn(beanstalkd_host, beanstalkd_port)


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
        global_stats['total_successes_percent'] = round(global_stats['total_successes'] * (global_stats['total_successes_and_failures'] / 100))
        global_stats['total_failures_percent'] = round(global_stats['total_failures'] * (global_stats['total_successes_and_failures'] / 100))

        return global_stats

    return {
        'total_successes': 0,
        'total_failures': 0,
        'total_successes_and_failures': 0,
        'total_successes_percent': 0,
        'total_failures_percent': 0
    }


def get_sample_file_path(sample_file_uuid, check_if_exists=False):
    sample_file_destination = os.path.abspath(app.config['SAMPLES_PATH'])
    sample_file_name = '{}.wav'.format(sample_file_uuid)
    sample_file_path = os.path.join(sample_file_destination, sample_file_name)

    if not os.path.exists(sample_file_path):
        raise Exception('The sample file does not exists')

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
