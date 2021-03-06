import requests

_ENDPOINT = 'https://secure.gaug.es/'
TOKEN = None


def _call(resource, method='GET'):
    url = _ENDPOINT + resource

    if TOKEN is None:
        raise Exception('Gauges token isn\'t defined')

    headers = {
        'X-Gauges-Token': TOKEN
    }

    response = requests.request(method, url, headers=headers)

    response_json = response.json()

    if not response.ok:
        message = response_json['message'] if 'message' in response_json else 'Unknow error'

        raise Exception(message)

    return response_json


def get_gauge(gauge_id):
    result = _call('gauges/' + gauge_id)

    return result['gauge']
