from war import app
import os

def get_sample_file_path(sample_file_uuid):
    sample_file_destination = os.path.abspath(app.config['SAMPLES_PATH'])
    sample_file_name = '{}.wav'.format(sample_file_uuid)
    sample_file_path = os.path.join(sample_file_destination, sample_file_name)

    return sample_file_path

def get_enabled_audio_databases():
    ret = {}

    enabled_audio_databases = app.config['ENABLED_AUDIO_DATABASES']

    audio_databases_module = __import__('audio_databases')

    for audio_database_classname in enabled_audio_databases:
        audio_database_class = getattr(audio_databases_module, audio_database_classname)
        audio_database_instance = audio_database_class()

        ret[audio_database_classname] = audio_database_instance

    return ret
