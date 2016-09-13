SECRET_KEY = 'secretkeyhere'
MONITORING_USERS = {}
SESSION_COOKIE_NAME = 'WAR'
DEBUG = False
MAX_CONTENT_LENGTH = 5 * 1024 * 1024
SAMPLES_PATH = 'storage/samples/'
LOGS_PATH = 'storage/logs/'
SAMPLE_DURATION = 10
LOGGER_HANDLER_POLICY = 'production'
GAUGES = {'API_TOKEN': 'blablah', 'SITE_ID': 'ahah'}
BUGSNAG = {'NOTIFIER_API_KEY': 'ahah', 'ORG_API_KEY': 'ahah', 'PROJECT_ID': 'ahah'}
MONGODB = {'HOST': '127.0.0.1', 'PORT': 27666}
BEANSTALKD = {'HOST': '127.0.0.1', 'PORT': 11666}
SUPERVISORD = {'HOST': '127.0.0.1', 'PORT': 9666}
PUSHER = {'APP_ID': 'ahah', 'KEY': 'ahah', 'SECRET': 'ahah', 'CLUSTER': 'eu'}
ENABLED_AUDIO_DATABASES = ('ACRCloud', 'Gracenote', 'AudibleMagic', 'MufinAudioID', 'AcoustID')
ACRCLOUD = {'HOST': 'eu-west-1.api.acrcloud.com', 'ACCESS_KEY': 'ahah', 'ACCESS_SECRET': 'ahah'}
OBJECT_STORE = {'AUTH_URL': 'https://auth.example.com/v2.0', 'STORAGE_URL': 'https://storage.loc1.example.com/v1/AUTH_', 'TENANT_ID': 'ahah', 'TENANT_NAME': 'ahah', 'USERNAME': 'ahah', 'PASSWORD': 'ahah', 'REGION_NAME': 'xxx'}
