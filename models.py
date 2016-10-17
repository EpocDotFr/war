from war import db
from enum import Enum
import arrow


news_tags_table = db.Table('news_tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='cascade'), primary_key=True, nullable=False),
    db.Column('news_id', db.Integer, db.ForeignKey('news.id', ondelete='cascade'), primary_key=True, nullable=False)
)

class Tag(db.Model):
    class TagQuery(db.Query):
        def get_all(self):
            q = self.join(Tag.news).filter(News.date != None, News.date <= arrow.now().datetime)

            results = q.all()

            return [tag.name for tag in results]

        def create_or_get(self, tags_list):
            q = self.filter(Tag.name.in_(tags_list))

            results = q.all()

            ret = []

            for list_tag in tags_list:
                for res_tag in results:
                    if list_tag == res_tag.name:
                        ret.append(res_tag)
                        break
                else:
                    ret.append(Tag(name=list_tag))

            return ret

    __tablename__ = 'tags'
    query_class = TagQuery

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    name = db.Column(db.String(255), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name


class News(db.Model):
    class NewsQuery(db.Query):
        def get_many(self, limit=None, admin=False, tag=None):
            q = self.order_by(News.date.desc())

            if not admin:
                q = q.filter(News.date != None, News.date <= arrow.now().datetime)

            if tag is not None:
                q = q.filter(News.tags.any(Tag.name == tag))

            if limit is not None:
                q = q.limit(limit)

            return q.all()

        def get_one_by_slug(self, slug):
            q = self.filter(News.slug == slug)

            return q.first()

        def get_latest(self):
            q = self.filter(News.date != None, News.date <= arrow.now().datetime)
            q = q.order_by(News.date.desc())

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

    @property
    def tags_list(self):
        return [tag.name for tag in self.tags]

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


class RecognitionRequest(db.Model):
    __tablename__ = 'recognition_requests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    uuid = db.Column(db.String(32), unique=True, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False)

    done_at = db.Column(db.DateTime,)
    sample_wav_url = db.Column(db.String(255))

    recognition_results = db.relationship('RecognitionResult', backref=db.backref('recognition_request', lazy='joined'))

    def __init__(self, uuid, submitted_at, done_at=None, sample_wav_url=None):
        self.uuid = uuid
        self.submitted_at = submitted_at

        self.done_at = done_at
        self.sample_wav_url = sample_wav_url

    def __repr__(self):
        return '<RecognitionRequest> #{} : {}'.format(self.id, self.uuid)


class RecognitionResultStatus(Enum):
    success = 'success'
    failure = 'failure'
    error = 'error'


class RecognitionResult(db.Model):
    class RecognitionResultQuery(db.Query):
        def get_many(self):
            pass

    __tablename__ = 'recognition_results'
    query_class = RecognitionResultQuery

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    recognition_request_id = db.Column(db.Integer, db.ForeignKey('recognition_requests.id', ondelete='cascade'), nullable=False)
    audio_database_id = db.Column(db.Integer, db.ForeignKey('audio_databases.id', ondelete='cascade'), nullable=False)
    is_final = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.Enum(RecognitionResultStatus), nullable=False)

    artist = db.Column(db.String(255))
    title = db.Column(db.String(255))
    infos = db.Column(db.Text)

    def __init__(self, is_final, status, recognition_request, audio_database, artist=None, title=None, infos=None):
        self.is_final = is_final
        self.status = status

        self.artist = artist
        self.title = title
        self.infos = infos

        self.recognition_request = recognition_request
        self.audio_database = audio_database

    def __repr__(self):
        return '<RecognitionResult> #{} : {}'.format(self.id, self.status)
