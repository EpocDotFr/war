Zepto(function () {
    navigator.getUserMedia = (navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia || navigator.msGetUserMedia);
    window.AudioContext = (window.AudioContext || window.webkitAudioContext);

    var audio_context = new window.AudioContext();
    var recorder;

    var div_progress = $('div#progress');
    var button_recognize = $('button#recognize');

    function onStreamConnected(stream) {
        window.audio_input = audio_context.createMediaStreamSource(stream);

        recorder = new Recorder(window.audio_input);
        recorder.record();

        displayStatus('info', 'Recording... Please wait {{ config['SAMPLE_DURATION'] }} seconds.');

        window.setTimeout(function() {
            recorder.stop();

            displayStatus('success', 'Recording ended');

            recorder.exportWAV(function(sample) {
                displayStatus('info', 'Sending sample...');

                var fd = new FormData();
                fd.append('sample', sample);

                $.ajax({
                    type: 'POST',
                    url: '{{ url_for('recognize') }}',
                    data: fd,
                    processData: false,
                    contentType: false,
                    success: function(data) {
                        displayStatus('success', 'Recognization request sent successfuly.');
                        recorder.clear();
                    },
                    error: function(xhr, type) {
                        displayStatus('error', 'Error sending recognization request.');
                    }
                });
            });
        }, {{ config['SAMPLE_DURATION'] * 1000 }});
    }

    function onStreamError(err) {
        displayStatus('error', 'Error while getting the recording device: '+err);
    }

    function displayStatus(type, message) {
        div_progress.text(message);
        div_progress.removeClass();
        div_progress.addClass('alert-'+type);
        div_progress.show();
    }

    button_recognize.on('click', function() {
        displayStatus('info', 'Waiting for the permission...');

        navigator.getUserMedia({audio: true}, onStreamConnected, onStreamError);
    });
});