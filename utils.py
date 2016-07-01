def get_sample_file_path(sample_file_uuid):
    sample_file_destination = os.path.abspath(app.config['SAMPLES_PATH'])
    sample_file_name = '{}.wav'.format(sample_file_uuid)
    sample_file_path = os.path.join(sample_file_destination, sample_file_name)

    return sample_file_path
