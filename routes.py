from flask import Response, jsonify, url_for, flash, redirect
from war import *
from urllib.parse import quote_plus
from flask_misaka import markdown
import xmlrpc.client
import bson
import PyRSS2Gen
import psutil
import bugsnag_client
import arrow
import sample_store
from models import *


# ----- Public routes -------

# Home page
@app.route('/')
def home():
    db = get_database()

    global_stats = get_global_stats(db)

    latest_news = get_latest_news(db)

    latest_success_samples = get_latest_success_samples(db)

    return render_template('home.html', global_stats=global_stats, latest_news=latest_news, latest_success_samples=latest_success_samples)


# About page
@app.route('/about')
def about():
    return render_template('about.html')


# Roadmap page
@app.route('/roadmap')
def roadmap():
    return render_template('roadmap.html')


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
    top_recognized_artists = get_top_recognized_artists(db)
    top_recognized_tracks = get_top_recognized_tracks(db)

    return render_template('stats.html',
                           audio_databases=audio_databases,
                           global_stats=global_stats,
                           top_recognized_artists=top_recognized_artists,
                           top_recognized_tracks=top_recognized_tracks)


# News list (can also be filtered by tag)
@app.route('/news', defaults={'tag': None})
@app.route('/news/tag/<tag>')
def news(tag):
    db = get_database()

    news_list = News.query.get_news_list(tag=tag)

    all_tags = None

    if tag is None:
        all_tags = get_all_news_tags(db)

    return render_template('news/list.html', news_list=news_list, tag=tag, all_tags=all_tags)


# RSS of the news
@app.route('/news/rss')
def news_rss():
    news_list = News.query.get_news_list(limit=5)

    rss_items = []

    for the_news in news_list:
        rss_items.append(PyRSS2Gen.RSSItem(
            title=the_news.title,
            link=url_for('one_news', slug=the_news.slug, _external=True),
            description=str(markdown(the_news.content, escape=True)),
            guid=PyRSS2Gen.Guid(url_for('one_news', slug=the_news.slug, _external=True)),
            pubDate=the_news.date,
            categories=the_news.tags
        ))

    rss = PyRSS2Gen.RSS2(
        title='Latest news from WAR (Web Audio Recognizer)',
        link=url_for('home', _external=True),
        description='Latest news from WAR (Web Audio Recognizer)',
        language='en',
        image=PyRSS2Gen.Image(url_for('static', filename='images/apple-icon-114x114.png', _external=True),
                              'Latest news from WAR (Web Audio Recognizer)',
                              url_for('home', _external=True)),
        lastBuildDate=arrow.now().datetime,
        items=rss_items
    )

    return Response(rss.to_xml(encoding='utf-8'), mimetype='application/rss+xml')


# One news
@app.route('/news/<slug>')
def one_news(slug):
    the_news = News.query.get_one_news_by_slug(slug)

    if the_news is None:
        abort(404)
    
    if the_news.date is None:
        g.INCLUDE_WEB_ANALYTICS = False
        g.NO_INDEX = True

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

            sample = create_one_sample(db)
            sample_id = str(sample.inserted_id)
            
            sample_store.save_locally(sample_file, sample_id)

            recognization_job_data = {'sample_id': sample_id}

            queue = get_queue()
            queue.use('war-samples-recognize')
            queue.put(json.dumps(recognization_job_data), delay=1)

            ajax_response['data']['sample_id'] = sample_id
        except Exception as e:
            app.logger.error(e)
            status = 500
            ajax_response['result'] = 'failure'
            ajax_response['data']['message'] = 'Sorry, there were a server error. We have been informed about this.'

    return jsonify(ajax_response), status


# Sample results
@app.route('/r/<sample_id>')
def results(sample_id):
    db = get_database()

    sample = None

    try:
        sample = get_one_sample_by_id(db, sample_id)
    except bson.errors.InvalidId:
        abort(404)

    if sample is None:
        abort(404)

    result = None
    
    if 'final_result' in sample and sample['final_result'] is not None:
        result = sample[sample['final_result']]

        if result['status'] == 'success':
            search_terms = []

            if 'artist' in result['data']:
                search_terms.append(result['data']['artist'])

            if 'title' in result['data']:
                search_terms.append(result['data']['title'])

            result['data']['search_terms'] = quote_plus(' '.join(search_terms))

    return render_template('results.html', sample=sample, result=result)


# RSS of the latest recognitions
@app.route('/recognitions/latest/rss')
def latest_recognitions_rss():
    db = get_database()

    samples_list = get_latest_success_samples(db, num=10)

    rss_items = []

    for sample in samples_list:
        result = sample[sample['final_result']]

        description = 'It is <strong>{}</strong> with <strong>{}</strong>{}.'.format(
            result['data']['artist'],
            result['data']['title'],
            ' from the album <strong>{}</strong>'.format(result['data']['album']) if 'album' in result['data'] else ''
        )

        rss_items.append(PyRSS2Gen.RSSItem(
            title=result['data']['artist'] + ' - ' + result['data']['title'],
            link=url_for('results', sample_id=sample['_id'], _external=True),
            description=description,
            guid=PyRSS2Gen.Guid(url_for('results', sample_id=sample['_id'], _external=True)),
            pubDate=sample['submitted_at'].datetime
        ))

    rss = PyRSS2Gen.RSS2(
        title='Latest recognitions from WAR (Web Audio Recognizer)',
        link=url_for('home', _external=True),
        description='Latest recognitions from WAR (Web Audio Recognizer)',
        language='en',
        image=PyRSS2Gen.Image(url_for('static', filename='images/apple-icon-114x114.png', _external=True),
                              'Latest recognitions from WAR (Web Audio Recognizer)',
                              url_for('home', _external=True)),
        lastBuildDate=arrow.now().datetime,
        items=rss_items
    )

    return Response(rss.to_xml(encoding='utf-8'), mimetype='application/rss+xml')


# Sitemap XML
@app.route('/sitemap.xml')
def sitemap_xml():
    app_routes = []

    news_list = News.query.get_news_list()

    for one_news in news_list:
        app_routes.append(url_for('one_news', slug=one_news['slug'], _external=True))

    return Response(render_template('sitemap.xml', routes=app_routes), mimetype='application/xml')

# ----- Private routes -------


# Managing dashboard
@app.route('/manage')
@auth.login_required
def manage():
    db = get_database()

    news_list = News.query.get_news_list(admin=True)
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
        ajax_response['data']['visits'] = gauges.get_gauge(app.config['GAUGES']['SITE_ID'])
    except Exception:
        pass

    try:
        ajax_response['data']['server'] = {
            'cpu': psutil.cpu_percent(interval=1),
            'ram': psutil.virtual_memory().percent,
            'hdd': psutil.disk_usage('/').percent
        }
    except Exception:
        pass

    try:
        push = get_push()

        ajax_response['data']['live_results'] = {
            'channels': len(push.channels_info('results-')['channels'])
        }
    except Exception:
        pass

    try:
        ajax_response['data']['errors'] = bugsnag_client.get_project_errors(app.config['BUGSNAG']['PROJECT_ID'],
                                                                            status='open')
    except Exception:
        pass

    try:
        xmlrpc_proxy = xmlrpc.client.ServerProxy('http://{}:{}/RPC2'.format(app.config['SUPERVISORD']['HOST'], app.config['SUPERVISORD']['PORT']))

        ajax_response['data']['processes'] = xmlrpc_proxy.supervisor.getAllProcessInfo()
    except Exception:
        pass

    try:
        ajax_response['data']['queues'] = []

        queue = get_queue()

        for tube in queue.tubes():
            if tube == 'default':
                continue

            ajax_response['data']['queues'].append(queue.stats_tube(tube))
    except Exception:
        pass

    return jsonify(ajax_response), status


# Create a news
@app.route('/manage/news/create', methods=['GET', 'POST'])
@auth.login_required
def news_create():
    db = get_database()

    if request.method == 'POST':
        create_one_news_result = create_one_news(db, request.form['title'], request.form['content'],
                                                 request.form['date'] if request.form['date'] != '' else None,
                                                 request.form['tags'] if request.form['tags'] != '' else None)

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

    the_news = get_one_news_by_id(db, news_id)

    if the_news is None:
        abort(404)

    if request.method == 'POST':
        if update_one_news(db, news_id, request.form['title'], request.form['content'],
                           request.form['date'] if request.form['date'] != '' else None,
                           request.form['tags'] if request.form['tags'] != '' else None):
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
    db = get_database()

    try:
        sample = get_one_sample_by_id(db, sample_id)
    except bson.errors.InvalidId:
        flash('The provided sample ID is invalid.', 'error')

        return redirect(url_for('manage'))

    if sample is None:
        flash('This sample doesn\'t exists.', 'error')

        return redirect(url_for('manage'))

    audio_databases = get_enabled_audio_databases(db)

    return render_template('manage/sample.html', sample=sample, audio_databases=audio_databases)


# Delete a sample
@app.route('/manage/samples/<sample_id>/delete')
@auth.login_required
def sample_manage_delete(sample_id):
    db = get_database()

    if delete_one_sample(db, sample_id):
        flash('Sample deleted successfuly.', 'success')
    else:
        flash('Error deleting this sample.', 'error')

    return redirect(url_for('manage'))


# Requeue a sample
@app.route('/manage/samples/<sample_id>/requeue')
@auth.login_required
def sample_manage_requeue(sample_id):
    recognization_job_data = {'sample_id': sample_id}

    queue = get_queue()
    queue.use('war-samples-recognize')
    queue.put(json.dumps(recognization_job_data))

    flash('Sample was requeued successfully.', 'success')

    return redirect(url_for('sample_manage', sample_id=sample_id))


# Unauthorized page
@app.route('/401')
def error_401():
    return http_error_handler(401)


# Forbidden page
@app.route('/403')
def error_403():
    return http_error_handler(403)


# Not Found page
@app.route('/404')
def error_404():
    return http_error_handler(404)


# Internal Server Error page
@app.route('/500')
def error_500():
    return http_error_handler(500)


# Service Unavailable page
@app.route('/503')
def error_503():
    return http_error_handler(503)
