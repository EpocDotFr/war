SECRET_KEY = 'secretkeyhere'
MONITORING_USERS = {}
SESSION_COOKIE_NAME = 'WAR'
DEBUG = False
MAX_CONTENT_LENGTH = 15 * 1024 * 1024
SAMPLES_PATH = 'storage/samples/'
LOGS_PATH = 'storage/logs/'
SAMPLE_DURATION = 10
LOGGER_HANDLER_POLICY = 'production'
GAUGES = {'API_TOKEN': 'blablah', 'SITE_ID': 'ahah'}
BUGSNAG = {'NOTIFIER_API_KEY': 'ahah', 'ORG_API_KEY': 'ahah', 'PROJECT_ID': 'ahah'}
MONGODB = {'HOST': '127.0.0.1', 'PORT': 27666}
BEANSTALKD = {'HOST': '127.0.0.1', 'PORT': 11666}
PUSHER = {'APP_ID': 'ahah', 'KEY': 'ahah', 'SECRET': 'ahah', 'CLUSTER': 'eu'}
ENABLED_AUDIO_DATABASES = ('ACRCloud', 'Gracenote', 'AudibleMagic', 'MufinAudioID', 'AcoustID')
ACRCLOUD = {'HOST': 'eu-west-1.api.acrcloud.com', 'ACCESS_KEY': 'ahah', 'ACCESS_SECRET': 'ahah'}
