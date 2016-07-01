from acrcloud.recognizer import ACRCloudRecognizer
from war import app
import json


class AudioDatabaseInterface:
    def website(self):
        raise NotImplementedError('Should be implemented')

    def name(self):
        raise NotImplementedError('Should be implemented')

    def recognize(self, sample_file_uuid):
        raise NotImplementedError('Should be implemented')


class ACRCloud(AudioDatabaseInterface):
    def website(self):
        return 'https://www.acrcloud.com/'

    def name(self):
        return 'ACRCloud'

    def recognize(self, sample_file_uuid):
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
        return json.loads(acrcloud.recognize_by_file(sample_file_path, 0))


class Gracenote(AudioDatabaseInterface):
    def website(self):
        return 'http://www.gracenote.com/'

    def name(self):
        return 'Gracenote'

    def recognize(self, sample_file_uuid):
        pass


class AudibleMagic(AudioDatabaseInterface):
    def website(self):
        return 'http://www.audiblemagic.com/'

    def name(self):
        return 'Audible Magic'

    def recognize(self, sample_file_uuid):
        pass


class MufinAudioID(AudioDatabaseInterface):
    def website(self):
        return 'https://www.mufin.com/'

    def name(self):
        return 'Mufin AudioID'

    def recognize(self, sample_file_uuid):
        pass


class AcoustID(AudioDatabaseInterface):
    def website(self):
        return 'https://acoustid.org/'

    def name(self):
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
