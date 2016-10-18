import sample_store
from war import app


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
                stat['successes_percent'] = 0 if stat['total'] == 0 else round(
                    (db_stats['successes'] * 100) / stat['total'])
                stat['failures_percent'] = 0 if stat['total'] == 0 else round(
                    (db_stats['failures'] * 100) / stat['total'])

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

        sample_file_path = sample_store.get_local_path(sample_id, check_if_exists=True)

        config = {
            'host': app.config['ACRCLOUD']['HOST'],
            'access_key': app.config['ACRCLOUD']['ACCESS_KEY'],
            'access_secret': app.config['ACRCLOUD']['ACCESS_SECRET'],
            'debug': app.config['DEBUG'],
            'timeout': 10
        }

        acrcloud = ACRCloudRecognizer(config)

        json_response = json.loads(acrcloud.recognize_by_file(sample_file_path, 0))

        results = {
            'status': 'success',
            'data': {}
        }

        if 'status' not in json_response:
            results['status'] = 'error'
            results['data']['message'] = 'The ACRCloud response is not valid'
            
            return results

        if json_response['status']['code'] == 1001:  # No results
            results['status'] = 'failure'

            return results

        if json_response['status']['code'] != 0:
            results['status'] = 'error'
            results['data']['message'] = json_response['status']['msg']

            return results

        if 'music' not in json_response['metadata']:
            results['status'] = 'failure'

            return results

        track = json_response['metadata']['music'][0]

        if 'album' in track:
            results['data']['album'] = track['album']['name']

        if 'artists' in track:
            results['data']['artist'] = track['artists'][0]['name']

        if 'title' in track:
            results['data']['title'] = track['title']

        return results


class GracenoteMusicID(AudioDatabaseInterface):
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
