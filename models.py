from war import db
from enum import Enum


class News(db.Model):
    __tablename__ = 'news'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    slug = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)

    date = db.Column(db.DateTime)
    content = db.Column(db.Text)
    tags = db.Column(db.String(255))

    def __init__(self, slug, title, date=None, content=None, tags=None):
        self.slug = slug
        self.title = title

        self.date = date
        self.content = content
        self.tags = tags

    def __repr__(self):
        return '<News> #{} : {}'.format(self.id, self.title)


class AudioDatabase(db.Model):
    __tablename__ = 'audio_databases'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    name = db.Column(db.String(255), nullable=False)
    class_name = db.Column(db.String(255), unique=True, nullable=False)
    website = db.Column(db.String(255), nullable=False)
    is_enabled = db.Column(db.Boolean, default=False, nullable=False)

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
    file_url = db.Column(db.String(255))

    def __init__(self, uuid, submitted_at, done_at=None, file_url=None):
        self.uuid = uuid
        self.submitted_at = submitted_at

        self.done_at = done_at
        self.file_url = file_url

    def __repr__(self):
        return '<Sample> #{} : {}'.format(self.id, self.uuid)


class SampleResultStatus(Enum):
    success = 'success'
    failure = 'failure'
    error = 'error'


class SampleResult(db.Model):
    __tablename__ = 'sample_results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    sample_id = db.Column(db.Integer, db.ForeignKey('samples.id'), nullable=False)
    audio_database_id = db.Column(db.Integer, db.ForeignKey('audio_databases.id'), nullable=False)
    is_final = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.Enum(SampleResultStatus), nullable=False)

    artist = db.Column(db.String(255))
    title = db.Column(db.String(255))
    infos = db.Column(db.Text)

    sample = db.relationship('Sample', backref=db.backref('sample_results', lazy='dynamic'))
    audio_database = db.relationship('AudioDatabase', backref=db.backref('sample_results', lazy='dynamic'))

    def __init__(self, is_final, status, sample, audio_database, artist=None, title=None, infos=None):
        self.is_final = is_final
        self.status = status

        self.artist = artist
        self.title = title
        self.infos = infos

        self.sample = sample
        self.audio_database = audio_database

    def __repr__(self):
        return '<Sample> #{} : {}'.format(self.id, self.status)
