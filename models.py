from war import *


class News(db.Document):
    title = db.StringField()
    date = db.DateTimeField(allow_none=True)
    content = db.StringField()
    slug = db.StringField()


class AudioDatabaseResult(db.Document):
    status = db.EnumField(db.StringField(), 'success', 'failure', 'error')
    data = db.KVField


class Sample(db.Document):
    done = db.BoolField(default=False)
    ACRCloud = db.DocumentField(AudioDatabaseResult, allow_none=True)
    submitted_at = db.DateTimeField()
    final_result = db.StringField(allow_none=True)
    file_url = db.StringField(allow_none=True)

    @computed_field
    def result(obj):
        return obj[obj.final_result] if 'final_result' in obj and obj.final_result is not None else None


class Stats(db.Document):
    failures = db.IntField()
    successes = db.IntField()
    audio_database = db.EnumField(db.StringField(), 'ACRCloud')
