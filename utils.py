from war import app
from pymongo import MongoClient
import os


def get_db():
    mongodb_host = app.config['MONGODB_HOST']
    mongodb_port = app.config['MONGODB_PORT']

    mongodb_client = MongoClient('mongodb://{}:{}'.format(mongodb_host, mongodb_port))

    return mongodb_client.war


def get_global_stats(db):
    global_stats = db.war.aggregate([
        {'$group': {
            '_id': None,
            'total_successes': {'$sum': '$successes'},
            'total_failures': {'$sum': '$failures'}
        }}
    ])

    # FIXME doesn't return at least one line with empty totals
    return list(global_stats)


def get_sample_file_path(sample_file_uuid):
    sample_file_destination = os.path.abspath(app.config['SAMPLES_PATH'])
    sample_file_name = '{}.wav'.format(sample_file_uuid)
    sample_file_path = os.path.join(sample_file_destination, sample_file_name)

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
