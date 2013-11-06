
from datetime import datetime
from pyelasticsearch import ElasticSearch
from pyelasticsearch.exceptions import ElasticHttpNotFoundError
from bson import ObjectId
from flask import request, json
from eve.io.base import DataLayer, ConnectionException
from eve.utils import config


DATE_FORMATS = (
    '%Y-%m-%dT%H:%M:%S.%f%z',
    '%Y-%m-%dT%H:%M:%S%z',
    '%Y-%m-%dT%H:%M:%S',
)

def parse_date(date_str):
    """Parse elastic datetime string."""
    for format in DATE_FORMATS:
        try:
            return datetime.strptime(date_str.replace('+00:', '+00'), format)
        except ValueError:
            pass
    return date_str

def convert_dates(doc):
    """Convert dates in doc into datetime objects.

    This should be supported by future version of pyelasticsearch.
    """
    if config.LAST_UPDATED in doc:
        doc[config.LAST_UPDATED] = parse_date(doc[config.LAST_UPDATED])

    if config.DATE_CREATED in doc:
        doc[config.DATE_CREATED] = parse_date(doc[config.DATE_CREATED])

class ElasticCursor(object):

    def __init__(self, hits):
        self.hits = hits;
        self.docs = []
        for hit in hits['hits']['hits']:
            doc = hit.get('fields', hit.get('_source', {}))
            doc[config.ID_FIELD] = hit.get('_id')
            convert_dates(doc)
            self.docs.append(doc)

    def __getitem__(self, key):
        return self.docs[key]

    def first(self):
        return self.docs[0] if self.docs else None

    def count(self):
        return self.hits['hits']['total']

class Elastic(DataLayer):

    def init_app(self, app):
        app.config.setdefault('ELASTICSEARCH_URL', 'http://localhost:9200/')
        app.config.setdefault('ELASTICSEARCH_INDEX', 'eve')
        self.es = app.extensions['elasticsearch'] = ElasticSearch(app.config['ELASTICSEARCH_URL'])
        self.index = app.config['ELASTICSEARCH_INDEX']

    def find(self, resource, req):
        args = dict()

        if req.max_results:
            args['size'] = req.max_results

        if req.page > 1:
            args['es_from'] = (req.page - 1) * req.max_results

        query = request.args.get('q', '*:*')
        if req.where:
            where = json.loads(req.where)
            if where:
                query = {
                    'query': {
                        'filtered': {
                            'query': {
                                'query_string': {
                                    'query': request.args.get('q', '*:*')
                                }
                            },
                            'filter': {
                                'term': where
                            }
                        }
                    }
                }

        datasource, filter_, projection = self._datasource_ex(resource)
        return self._parse_hits(self.es.search(query=query, index=self.index, doc_type=datasource, es_fields=self._fields(projection),  **args))

    def find_one(self, resource, **lookup):
        datasource, filter_, projection = self._datasource_ex(resource, lookup)

        if config.ID_FIELD in lookup:
            hit = self.es.get(self.index, datasource, id=lookup[config.ID_FIELD], fields=self._fields(projection))
            if not hit['exists']:
                return
            doc = hit.get('fields', hit.get('_source', {}))
            doc['_id'] = hit.get('_id')
            convert_dates(doc)
            return doc
        else:
            query = {
                'query': {
                    'constant_score': {
                        'filter': {
                            'term': lookup
                        }
                    }
                }
            }

            try:
                docs = self._parse_hits(self.es.search(query, index=self.index, doc_type=datasource, size=1, es_fields=self._fields(projection)))
                return docs.first()
            except ElasticHttpNotFoundError:
                return None

    def find_list_of_ids(self, resource, ids, client_projection=None):
        datasource, filter_, fields = self._datasource_ex(resource)
        return self._parse_hits(self.es.multi_get(ids, self.index, dataresource, fields))

    def insert(self, resource, doc_or_docs):
        datasource, filter_, _ = self._datasource_ex(resource)

        ids = []
        for doc in doc_or_docs:
            doc.update(self.es.index(self.index, datasource, doc, id=doc.get('_id')))
            ids.append(doc['_id'])
        self.es.refresh(self.index)
        return ids

    def update(self, resource, id_, updates):
        datasource, filter_, _ = self._datasource_ex(resource)
        return self.es.update(self.index, datasource, id_, doc=updates, refresh=True)

    def replace(self, resource, id_, document):
        datasource, filter_, _ = self._datasource_ex(resource)
        return self.es.index(self.index, datasource, document, id=id_, overwrite_existing=True, refresh=True)

    def remove(self, resource, id_=None):
        datasource, filter_, _ = self._datasource_ex(resource)
        if id_:
            return self.es.delete(self.index, datasource, id=id_, refresh=True)
        else:
            try:
                self.es.delete_all(self.index, datasource)
                return self.es.refresh(self.index)
            except ElasticHttpNotFoundError:
                return

    def _parse_hits(self, hits):
        """Parse hits response into documents."""
        return ElasticCursor(hits)

    def _fields(self, projection):
        keys = projection.keys()
        return ','.join(keys)
