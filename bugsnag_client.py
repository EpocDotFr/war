import requests

_ENDPOINT = 'https://api.bugsnag.com/'
API_KEY = None


def _call(resource, method='GET', params=None):
    url = _ENDPOINT + resource

    if API_KEY is None:
        raise Exception('Bugsnag API key isn\'t defined')

    headers = {
        'Authorization': 'token {}'.format(API_KEY)
    }

    response = requests.request(method, url, headers=headers, params=params)

    response_json = response.json()

    if not response.ok:
        message = response_json['error'] if 'error' in response_json else 'Unknow error'

        raise Exception(message)

    return response_json


def get_project_errors(project_id, status=None):
    params = None

    if status is not None:
        if params is None:
            params = {}

        params['status'] = status

    return _call('projects/{}/errors'.format(project_id), params=params)
