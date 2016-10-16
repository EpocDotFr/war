from war import db
from enum import Enum
import arrow


news_tags_table = db.Table('news_tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), nullable=False),
    db.Column('news_id', db.Integer, db.ForeignKey('news.id'), nullable=False)
)

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    name = db.Column(db.String(255), nullable=False)

    def __init__(self, name):
        self.name = name


class News(db.Model):
    class NewsQuery(db.Query):
        def get_many(self, limit=None, admin=False, tag=None):
            q = self.order_by(News.date.desc())

            if not admin:
                q = q.filter(News.date != None, News.date <= arrow.now().datetime)

            if tag is not None:
                pass # TODO

            if limit is not None:
                q.limit(limit)

            return q.all()

        def get_one_by_slug(self, slug):
            q = self.filter(News.slug == slug)

            return q.first()

        def get_latest(self):
            q = self.filter(News.date != None, News.date <= arrow.now().datetime)
            q.order_by(News.date.desc())

            return q.first()

    __tablename__ = 'news'
    query_class = NewsQuery

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    slug = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)

    date = db.Column(db.DateTime)
    content = db.Column(db.Text)
    tags = db.relationship('Tag', secondary=news_tags_table, backref=db.backref('news', lazy='dynamic'))

    def __init__(self, slug, title, date=None, content=None, tags=None):
        self.slug = slug
        self.title = title

        self.date = date
        self.content = content
        self.tags = tags

    def __repr__(self):
        return '<News> #{} : {}'.format(self.id, self.title)

    @property
    def date_arrowed(self):
        return arrow.get(self.date) if self.date is not None else None


class AudioDatabase(db.Model):
    __tablename__ = 'audio_databases'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    name = db.Column(db.String(255), nullable=False)
    class_name = db.Column(db.String(255), unique=True, nullable=False)
    website = db.Column(db.String(255), nullable=False)
    is_enabled = db.Column(db.Boolean, default=False, nullable=False)

    recognition_results = db.relationship('RecognitionResult', backref=db.backref('audio_database', lazy='joined'))

    def __init__(self, name, class_name, website, is_enabled=False):
        self.name = name
        self.class_name = class_name
        self.website = website
        self.is_enabled = is_enabled

    def __repr__(self):
        return '<AudioDatabase> #{} : {}'.format(self.id, self.name)


class Sample(db.Model):
    __tablename__ = 'samples'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    uuid = db.Column(db.String(32), unique=True, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False)

    done_at = db.Column(db.DateTime,)
    wav_file_url = db.Column(db.String(255))

    recognition_results = db.relationship('RecognitionResult', backref=db.backref('sample', lazy='joined'))

    def __init__(self, uuid, submitted_at, done_at=None, wav_file_url=None):
        self.uuid = uuid
        self.submitted_at = submitted_at

        self.done_at = done_at
        self.wav_file_url = wav_file_url

    def __repr__(self):
        return '<Sample> #{} : {}'.format(self.id, self.uuid)


class RecognitionResultStatus(Enum):
    success = 'success'
    failure = 'failure'
    error = 'error'


class RecognitionResult(db.Model):
    __tablename__ = 'recognition_results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'), nullable=False)
    audio_database_id = db.Column(db.Integer, db.ForeignKey('audio_databases.id'), nullable=False)
    is_final = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.Enum(RecognitionResultStatus), nullable=False)

    artist = db.Column(db.String(255))
    title = db.Column(db.String(255))
    infos = db.Column(db.Text)

    def __init__(self, is_final, status, sample, audio_database, artist=None, title=None, infos=None):
        self.is_final = is_final
        self.status = status

        self.artist = artist
        self.title = title
        self.infos = infos

        self.sample = sample
        self.audio_database = audio_database

    def __repr__(self):
        return '<RecognitionResult> #{} : {}'.format(self.id, self.status)
