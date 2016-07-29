from flask import Response, jsonify, url_for, flash, redirect
from war import *
import bson
import PyRSS2Gen
import psutil


# ----- Public routes -------

# Home page
@app.route('/')
def home():
    db = get_database()

    global_stats = get_global_stats(db)

    latest_news = None

    latest_news = get_latest_news(db)

    return render_template('home.html', global_stats=global_stats, latest_news=latest_news)


# About page
@app.route('/about')
def about():
    return render_template('about.html')


# FAQ page
@app.route('/faq')
def faq():
    return render_template('faq.html')


# Terms of service page
@app.route('/tos')
def tos():
    return render_template('tos.html')


# Stats page
@app.route('/stats')
def stats():
    db = get_database()

    audio_databases = get_enabled_audio_databases(db)
    global_stats = get_global_stats(db)

    return render_template('stats.html', audio_databases=audio_databases, global_stats=global_stats)


# News list
@app.route('/news')
def news():
    db = get_database()

    news_list = get_news_list(db)

    return render_template('news/list.html', news_list=news_list)


# RSS of the news
@app.route('/news/rss')
def news_rss():
    db = get_database()

    news_list = get_news_list(db, limit=5)

    rss_items = []

    for the_news in news_list:
        rss_items.append(PyRSS2Gen.RSSItem(
            title=the_news['title'],
            link=url_for('one_news', slug=the_news['slug'], _external=True),
            description=the_news['content'],
            guid=PyRSS2Gen.Guid(url_for('one_news', slug=the_news['slug'], _external=True)),
            pubDate=the_news['date'].datetime
        ))

    rss = PyRSS2Gen.RSS2(
        title='Latest news from WAR (Web Audio Recognizer)',
        link=url_for('home', _external=True),
        description='Latest news from WAR (Web Audio Recognizer)',
        language='en',
        image=PyRSS2Gen.Image(url_for('static', filename='images/logo_128.png'), 'Logo of WAR',
                              url_for('home', _external=True)),
        lastBuildDate=arrow.now().datetime,
        items=rss_items
    )

    return Response(rss.to_xml(encoding='utf-8'), mimetype='application/rss+xml')


# One news
@app.route('/news/<slug>')
def one_news(slug):
    db = get_database()

    the_news = get_one_news_by_slug(db, slug)

    if the_news is None:
        abort(404)

    return render_template('news/one.html', the_news=the_news)


# Sample recognization
@app.route('/recognize', methods=['POST'])
def recognize():
    ajax_response = {
        'result': 'success',
        'data': {}
    }

    status = 202

    if not request.is_xhr or 'sample' not in request.files:
        app.logger.warning('Invalid request')
        status = 400
        ajax_response['result'] = 'failure'
        ajax_response['data']['message'] = 'Invalid request'
    else:
        sample_file = request.files['sample']

        try:
            db = get_database()

            enabled_audio_databases = app.config['ENABLED_AUDIO_DATABASES']

            db_data = {
                'done': False
            }

            for audio_database_classname in enabled_audio_databases:
                db_data[audio_database_classname] = None

            sample = db.samples.insert_one(db_data)

            sample_id = str(sample.inserted_id)

            recognization_job_data = {'sample_id': sample_id}

            queue = get_queue()
            queue.use('samples')
            queue.put(json.dumps(recognization_job_data))

            sample_file_path = get_sample_file_path(sample_id)
            sample_file.save(sample_file_path)

            ajax_response['data']['sample_id'] = sample_id
        except Exception as e:
            app.logger.error(str(e))
            status = 500
            ajax_response['result'] = 'failure'
            ajax_response['data']['message'] = 'Sorry, there were a server error. We have been informed about this.'

    return jsonify(ajax_response), status


# Sample results
@app.route('/r/<sample_id>')
def results(sample_id):
    g.NO_INDEX = True

    try:
        sample_id_object = ObjectId(sample_id)
    except bson.errors.InvalidId as bei:
        abort(404)

    db = get_database()

    sample = db.samples.find_one({'_id': sample_id_object})

    if sample is None:
        abort(404)

    res = []

    audio_databases = get_enabled_audio_databases(db)

    for audio_database_id, audio_database_instance in audio_databases.items():
        if audio_database_id in sample and sample[audio_database_id] is not None:
            if sample[audio_database_id] is False:
                res.append({
                    'audio_database_id': audio_database_id,
                    'audio_database_name': audio_database_instance.get_name()
                })
            else:
                search_terms = []

                if 'artist' in sample[audio_database_id]:
                    search_terms.append(sample[audio_database_id]['artist'])

                if 'title' in sample[audio_database_id]:
                    search_terms.append(sample[audio_database_id]['title'])

                    res.append({
                        'audio_database_id': audio_database_id,
                        'audio_database_name': audio_database_instance.get_name(),
                        'track': sample[audio_database_id],
                        'search_terms': quote_plus(' '.join(search_terms))
                    })

    return render_template('results.html', sample=sample, results=res)


# Sitemap XML
@app.route('/sitemap.xml')
def sitemap_xml():
    routes = []

    db = get_database()

    news_list = get_news_list(db)

    for news in news_list:
        routes.append(url_for('one_news', slug=news['slug'], _external=True))

    return Response(render_template('sitemap.xml', routes=routes), mimetype='application/xml')


# ----- Private routes -------


# Managing dashboard
@app.route('/manage')
@auth.login_required
def manage():
    db = get_database()

    news_list = get_news_list(db, admin=True)
    global_stats = get_global_stats(db)

    return render_template('manage/home.html', news_list=news_list, global_stats=global_stats)


# Managing dashboard data
@app.route('/manage/data')
@auth.login_required
def manage_get_data():
    ajax_response = {
        'result': 'success',
        'data': {}
    }

    status = 200

    try:
        ajax_response['data']['visits'] = gauges.get_gauge(app.config['GAUGES_SITE_ID'])
    except Exception as e:
        pass

    try:
        ajax_response['data']['server'] = {
            'cpu': psutil.cpu_percent(interval=1),
            'ram': psutil.virtual_memory().percent,
            'hdd': psutil.disk_usage('/').percent
        }
    except Exception as e:
        pass

    try:
        push = get_push()

        ajax_response['data']['live_results'] = {
            'channels': len(push.channels_info('results-')['channels'])
        }
    except Exception as e:
        print(e)

    return jsonify(ajax_response), status


# Create a news
@app.route('/manage/news/create', methods=['GET', 'POST'])
@auth.login_required
def news_create():
    db = get_database()

    if request.method == 'POST':
        create_one_news_result = create_one_news(db, request.form['title'], request.form['content'], request.form['date'] if request.form['date'] != '' else None)

        if create_one_news_result.inserted_id:
            flash('News created successfuly.', 'success')

            return redirect(url_for('news_edit', news_id=str(create_one_news_result.inserted_id)))
        else:
            flash('Error creating this news.', 'error')

    return render_template('manage/news/create.html')


# Edit a news
@app.route('/manage/news/edit/<news_id>', methods=['GET', 'POST'])
@auth.login_required
def news_edit(news_id):
    db = get_database()

    the_news = get_one_news_by_id(db, news_id, markdown=True)

    if the_news is None:
        abort(404)

    if request.method == 'POST':
        if update_one_news(db, news_id, request.form['title'], request.form['content'], request.form['date'] if request.form['date'] != '' else None):
            flash('News edited successfuly.', 'success')

            return redirect(url_for('news_edit', news_id=the_news['_id']))
        else:
            flash('Error editing this news.', 'error')

    return render_template('manage/news/edit.html', the_news=the_news)


# Delete a news
@app.route('/manage/news/delete/<news_id>')
@auth.login_required
def news_delete(news_id):
    db = get_database()

    if delete_one_news(db, news_id):
        flash('News deleted successfuly.', 'success')
    else:
        flash('Error deleting this news.', 'error')

    return redirect(url_for('manage'))


# Manage a sample
@app.route('/manage/samples/<sample_id>')
@auth.login_required
def sample_manage(sample_id):
    try:
        sample_id_object = ObjectId(sample_id)
    except bson.errors.InvalidId as bei:
        flash('The provided sample ID is invalid.', 'error')

        return redirect(url_for('manage'))

    db = get_database()

    sample = db.samples.find_one({'_id': sample_id_object})

    if sample is None:
        flash('This sample doesn\'t exists.', 'error')

        return redirect(url_for('manage'))

    return render_template('manage/sample.html', sample=sample)


# ----- Error routes -------


# Unauthorized
@app.errorhandler(401)
def error_401(error):
    return render_template('errors/401.html'), 401


# Forbidden
@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html'), 403


# Not Found
@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html'), 404


# Internal Server Error
@app.errorhandler(500)
def error_500(error):
    app.logger.error(str(error))
    return render_template('errors/500.html'), 500


# Service Unavailable
@app.errorhandler(503)
def error_503(error):
    return render_template('errors/503.html'), 503
