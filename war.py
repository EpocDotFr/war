from flask import Flask, render_template, jsonify, request, abort
import os
import uuid
import acoustid

app = Flask(__name__)
app.config.from_pyfile('config.py')


# Home page with the Recognize button
@app.route('/')
def home():
    return render_template('home.html')


# Receive and handle the sample WAV file via AJAX upload
@app.route('/sample', methods=['POST'])
def sample():
    result = {
        'result': 'failure',
        'data': {}
    }

    if not request.is_xhr or not request.files['file']:
        result['data']['message'] = 'Bad request.'
        abort(400, result)  # FIXME improve this to return proper JSON

    try:
        sample_file = request.files['file']

        sample_file_uuid = uuid.uuid4()

        sample_file.save(get_sample_file_path(sample_file_uuid))

        # TODO everything after this line is temporary

        generate_fingerprint(sample_file_uuid)

        # TODO end temporary
    except Exception as e:
        result['data']['message'] = str(e)
        abort(500, result)  # FIXME improve this to return proper JSON

    return jsonify(result)


# Not Found
@app.errorhandler(404)
def error_404(error):
    return render_template('404.html', error=error)


# Internal Server Error
@app.errorhandler(500)
def error_500(error):
    return render_template('500.html', error=error)

# TODO put all functions bellow in a module

def get_sample_file_path(sample_file_uuid):
    sample_file_destination = os.path.abspath(app.config['SAMPLES_PATH'])
    sample_file_name = '{}.wav'.format(sample_file_uuid)
    sample_file_path = os.path.join(sample_file_destination, sample_file_name)

    return sample_file_path


def generate_fingerprint(sample_file_uuid):
    sample_file_path = get_sample_file_path(sample_file_uuid)

    if not os.path.exists(sample_file_path):
        raise Exception('The sample file does not exists anymore.')

    print(acoustid.fingerprint_file(sample_file_path))
