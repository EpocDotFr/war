from war import app
import swiftclient
import os


def _get_remote_connection():
    connection = swiftclient.Connection(
        authurl=app.config['AUTH_URL'],
        user=app.config['USERNAME'],
        key=app.config['PASSWORD'],
        tenant_name=app.config['TENANT_NAME'],
        auth_version='2',
        os_options={'tenant_id': app.config['TENANT_ID'], 'region_name': 'GRA1'}
    )

    # connection.put_object(app.config['CONTAINER_URL'], container='samples', name='test')


def save_locally(file, sample_id):
    sample_file_path = get_local_path(sample_id)

    file.save(sample_file_path)


def save_remotely(file, sample_id):
    pass # TODO


def get_local_path(sample_id, check_if_exists=False):
    sample_file_destination = os.path.abspath(app.config['SAMPLES_PATH'])
    sample_file_name = '{}.wav'.format(sample_id)
    sample_file_path = os.path.join(sample_file_destination, sample_file_name)

    if check_if_exists and not os.path.exists(sample_file_path):
        raise Exception('The sample file "{}" does not exists on the file system'.format(sample_file_path))

    return sample_file_path


def get_remote_path(sample):
    return sample['remote_url'] if 'remote_url' in sample and sample['remote_url'] is not None else None


def delete_locally(sample_id):
    sample_file_path = get_local_path(sample_id)

    if os.path.exists(sample_file_path):
        os.remove(sample_file_path)


def delete_remotely(sample_id):
    pass # TODO
