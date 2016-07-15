from war import app
from utils import get_sample_file_path


class AudioDatabaseInterface:
    db = None
    stats = None

    def __init__(self, db):
        self.db = db

    def get_website(self):
        raise NotImplementedError('Should be implemented')

    def get_name(self):
        raise NotImplementedError('Should be implemented')

    def recognize(self, sample_id):
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

                stat['total'] = 0
                stat['successes_percent'] = 0
                stat['failures_percent'] = 0
            else:
                stat['successes'] = db_stats['successes']
                stat['failures'] = db_stats['failures']
                stat['total'] = db_stats['successes'] + db_stats['failures']
                stat['successes_percent'] = round(db_stats['successes'] * (stat['total'] / 100))
                stat['failures_percent'] = round(db_stats['failures'] * (stat['total'] / 100))

            self.stats = stat

        return self.stats


class ACRCloud(AudioDatabaseInterface):
    def get_website(self):
        return 'https://www.acrcloud.com/'

    def get_name(self):
        return 'ACRCloud'

    def recognize(self, sample_id):
        from acrcloud.recognizer import ACRCloudRecognizer
        from flask import json

        sample_file_path = get_sample_file_path(sample_id, check_if_exists=True)

        config = {
                'host': app.config['ACRCLOUD_HOST'],
                'access_key': app.config['ACRCLOUD_ACCESS_KEY'],
                'access_secret': app.config['ACRCLOUD_ACCESS_SECRET'],
                'debug': app.config['DEBUG'],
                'timeout': 10
        }

        acrcloud = ACRCloudRecognizer(config)

        json_response = json.loads(acrcloud.recognize_by_file(sample_file_path, 0))

        if 'status' not in json_response:
            raise Exception('The ACRCloud response is not valid')

        if json_response['status']['code'] == 1001: # No result
            return False

        if json_response['status']['code'] != 0:
            raise Exception(json_response['status']['msg'])

        if 'music' not in json_response['metadata']:
            return False

        track = json_response['metadata']['music'][0]

        results = {}

        if 'album' in track:
            results['album'] = track['album']['name']

        if 'artist' in track:
            results['artist'] = track['artists'][0]['name']

        if 'title' in track:
            results['title'] = track['title']

        return results


class Gracenote(AudioDatabaseInterface):
    def get_website(self):
        return 'http://www.gracenote.com/'

    def get_name(self):
        return 'Gracenote'

    def recognize(self, sample_id):
        pass


class AudibleMagic(AudioDatabaseInterface):
    def get_website(self):
        return 'http://www.audiblemagic.com/'

    def get_name(self):
        return 'Audible Magic'

    def recognize(self, sample_id):
        pass


class MufinAudioID(AudioDatabaseInterface):
    def get_website(self):
        return 'https://www.mufin.com/'

    def get_name(self):
        return 'Mufin AudioID'

    def recognize(self, sample_id):
        pass


class AcoustID(AudioDatabaseInterface):
    def get_website(self):
        return 'https://acoustid.org/'

    def get_name(self):
        return 'AcoustID'

    def recognize(self, sample_id):
        pass
        # sample_file_path = get_sample_file_path(sample_id, True)

        # fingerprint = acoustid.fingerprint_file(sample_file_path)
        
        # app.logger.info('Result: {}'.format(fingerprint[1]))
        # app.logger.info('Sending match request to AcoustID')
        
        # lookup_results = acoustid.lookup(app.config['ACOUSTID_API_KEY'], fingerprint[1], fingerprint[0])
        
        # if not lookup_results['status'] or lookup_results['status'] != 'ok':
        #     raise Exception(lookup_results['message'])
        
        # return lookup_results['results']
