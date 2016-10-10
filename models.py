from war import *
from flask_mongoalchemy import BaseQuery
import arrow


class NewsQuery(BaseQuery):
    def get_news_list(self, limit=None, admin=False, tag=None):
        if not admin:
            self.not_(News.date == None)
            self.filter(News.date <= arrow.now().datetime)

        if tag is not None:
            self.in_(News.tags, tag)

        if limit is not None:
            self.limit(limit)

        self.ascending(News.date)

        return self.all()

    def get_one_news_by_slug(self, slug):
        self.filter(News.slug == slug)

        return self.one()

    def get_all_news_tags(self): # FIXME doesn't work: returns documents
        self.not_(News.date == None)
        self.filter(News.date <= arrow.now().datetime)
        
        return self.distinct(News.tags)


class News(db.Document):
    config_collection_name = 'news'
    query_class = NewsQuery

    title = db.StringField()
    date = db.DateTimeField(allow_none=True, default=None)
    content = db.StringField()
    slug = db.StringField()
    tags = db.ListField(db.StringField())

    @db.computed_field(db.StringField(), deps=[date])
    def date_humanized(obj):
        return arrow.get(obj.get('date')).humanize() if obj.get('date') is not None else None


class AudioDatabaseResult(db.Document):
    status = db.EnumField(db.StringField(), 'success', 'failure', 'error')
    data = db.AnythingField() # TODO


class Sample(db.Document):
    config_collection_name = 'samples'

    done = db.BoolField(default=False)
    ACRCloud = db.DocumentField(AudioDatabaseResult, allow_none=True, default=None)
    submitted_at = db.DateTimeField()
    final_result = db.EnumField(db.StringField(), 'ACRCloud', allow_none=True, default=None)
    file_url = db.StringField(allow_none=True, default=None)

    @db.computed_field(db.DocumentField(AudioDatabaseResult), deps=[final_result])
    def result(obj):
        return obj[obj.get('final_result')] if 'final_result' in obj and obj.get('final_result') is not None else None


class Stats(db.Document):
    config_collection_name = 'stats'

    failures = db.IntField()
    successes = db.IntField()
    audio_database = db.EnumField(db.StringField(), 'ACRCloud')
