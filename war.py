from flask import Flask, render_template, jsonify, request, abort
import os, uuid

app = Flask(__name__)
app.config.from_pyfile('config.py')

# Home page with the Recognize button
@app.route('/')
def home():
    return render_template('home.html')

# Receive and handle the sample WAV file
@app.route('/sample', methods=['POST'])
def sample():
    result = {
        'result': 'failure',
        'data': {}
    }

    if not request.is_xhr or not request.files['file']:
        result['data']['message'] = 'Bad request.'
        abort(400, result)

    try:
        sample_file = request.files['file']

        sample_file_destination = os.path.abspath(app.config['SAMPLES_PATH'])
        sample_file_name = '{}.wav'.format(uuid.uuid4())

        sample_file.save(os.path.join(sample_file_destination, sample_file_name))
    except Exception as e:
        result['data']['message'] = str(e)
        abort(500, result)

    return jsonify(result)

# Not Found
@app.errorhandler(404)
def error_404(error):
    return render_template('404.html', error=error)

# Internal Server Error
@app.errorhandler(500)
def error_500(error):
    return render_template('500.html', error=error)