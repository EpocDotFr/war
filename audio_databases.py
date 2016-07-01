from acrcloud.recognizer import ACRCloudRecognizer
import json


class AudioDatabaseInterface:
	name = None

	def __init__(self, name):
		self.name = name

    def recognize(self, sample_file_uuid):
		raise NotImplementedError('Should be implemented')


class ACRCloud(AudioDatabaseInterface):
	def __init__(self):
		super().__init__('ACRCloud')

    def recognize(self, sample_file_uuid):
	    sample_file_path = get_sample_file_path(sample_file_uuid)

	    if not os.path.exists(sample_file_path):
	        raise Exception('The sample file does not exists')

        config = {
                'host': 'eu-west-1.api.acrcloud.com',
                'access_key': '572705ff4cb98dd76eede63c7a72d825',
                'access_secret': 'vwagGtTe062U3XgqkRhV1Se9FJIC369Wu2Sibb8F',
                'debug': False,
                'timeout': 10
        }

        acrcloud = ACRCloudRecognizer(config)

    	# TODO handle errors from response
        return json.loads(acrcloud.recognize_by_file(sample_file_path, 0))


class Gracenote(AudioDatabaseInterface):
	def __init__(self):
		super().__init__('Gracenote')

    def recognize(self, sample_file_uuid):
    	pass


class AudibleMagic(AudioDatabaseInterface):
	def __init__(self):
		super().__init__('Audible Magic')

    def recognize(self, sample_file_uuid):
    	pass


class MufinAudioID(AudioDatabaseInterface):
	def __init__(self):
		super().__init__('Mufin AudioID')

    def recognize(self, sample_file_uuid):
    	pass


class AcoustID(AudioDatabaseInterface):
	def __init__(self):
		super().__init__('AcoustID')

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
