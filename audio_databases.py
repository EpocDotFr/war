from war import app
from utils import get_sample_file_path
import os


class AudioDatabaseInterface:
    db = None
    stats = None

    def __init__(self, db):
        self.db = db

    def get_website(self):
        raise NotImplementedError('Should be implemented')

    def get_name(self):
        raise NotImplementedError('Should be implemented')

    def recognize(self, sample_file_uuid):
        raise NotImplementedError('Should be implemented')

    def get_stats(self):
        audio_database = self.__class__.__name__

        if self.stats is None:
            db_stats = self.db.stats.find_one({'audio_database': audio_database})

            stat = {
                'successes': 0,
                'failures': 0
            }

            if db_stats is None:
                self.db.stats.insert_one({
                    **{
                        'audio_database': audio_database
                    },
                    **stat
                })
            else:
                stat['successes'] = db_stats['successes']
                stat['failures'] = db_stats['failures']

            self.stats = stat

        return self.stats


class ACRCloud(AudioDatabaseInterface):
    def get_website(self):
        return 'https://www.acrcloud.com/'

    def get_name(self):
        return 'ACRCloud'

    def recognize(self, sample_file_uuid):
        from acrcloud.recognizer import ACRCloudRecognizer
        import json

        sample_file_path = get_sample_file_path(sample_file_uuid)

        if not os.path.exists(sample_file_path):
            raise Exception('The sample file does not exists')

        config = {
                'host': app.config['ACRCLOUD_HOST'],
                'access_key': app.config['ACRCLOUD_ACCESS_KEY'],
                'access_secret': app.config['ACRCLOUD_ACCESS_SECRET'],
                'debug': app.config['DEBUG'],
                'timeout': 10
        }

        acrcloud = ACRCloudRecognizer(config)

        # TODO handle errors from response
        # TODO make response the same along others
        # TODO MongoDB find_one_and_update
        return json.loads(acrcloud.recognize_by_file(sample_file_path, 0))


class Gracenote(AudioDatabaseInterface):
    def get_website(self):
        return 'http://www.gracenote.com/'

    def get_name(self):
        return 'Gracenote'

    def recognize(self, sample_file_uuid):
        pass


class AudibleMagic(AudioDatabaseInterface):
    def get_website(self):
        return 'http://www.audiblemagic.com/'

    def get_name(self):
        return 'Audible Magic'

    def recognize(self, sample_file_uuid):
        pass


class MufinAudioID(AudioDatabaseInterface):
    def get_website(self):
        return 'https://www.mufin.com/'

    def get_name(self):
        return 'Mufin AudioID'

    def recognize(self, sample_file_uuid):
        pass


class AcoustID(AudioDatabaseInterface):
    def get_website(self):
        return 'https://acoustid.org/'

    def get_name(self):
        return 'AcoustID'

    def recognize(self, sample_file_uuid):
        sample_file_path = get_sample_file_path(sample_file_uuid)

        if not os.path.exists(sample_file_path):
            raise Exception('The sample file does not exists')
        
        # fingerprint = acoustid.fingerprint_file(sample_file_path)
        
        # app.logger.info('Result: {}'.format(fingerprint[1]))
        # app.logger.info('Sending match request to AcoustID')
        
        # lookup_results = acoustid.lookup(app.config['ACOUSTID_API_KEY'], fingerprint[1], fingerprint[0])
        
        # if not lookup_results['status'] or lookup_results['status'] != 'ok':
        #     raise Exception(lookup_results['message'])
        
        # return lookup_results['results']
