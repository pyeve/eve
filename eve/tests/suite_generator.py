from datetime import datetime


class EmbeddedDoc:
    def __init__(self, _id):
        self._id = _id
        self._created = datetime.utcnow()
