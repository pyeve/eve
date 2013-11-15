
import ast
import arrow
from pyelasticsearch import ElasticSearch
from pyelasticsearch.exceptions import ElasticHttpNotFoundError, ElasticHttpError, IndexAlreadyExistsError
from bson import ObjectId
from flask import request, json
from eve.io.base import DataLayer, ConnectionException
from eve.utils import config

def parse_date(date_str):
    """Parse elastic datetime string."""
    return arrow.get(date_str).datetime

def convert_dates(doc):
    """Convert dates in doc into datetime objects.

    This should be supported by future version of pyelasticsearch.
    """
    if config.LAST_UPDATED in doc:
        doc[config.LAST_UPDATED] = parse_date(doc[config.LAST_UPDATED])

    if config.DATE_CREATED in doc:
        doc[config.DATE_CREATED] = parse_date(doc[config.DATE_CREATED])

class ElasticCursor(object):
    """Search results cursor."""

    no_hits = {'hits': {'total': 0, 'hits': []}}

    def __init__(self, hits=None):
        """Parse hits into docs."""
        self.hits = hits if hits else self.no_hits
        self.docs = []

        for hit in self.hits['hits']['hits']:
            doc = hit.get('fields', hit.get('_source', {}))
            doc[config.ID_FIELD] = hit.get('_id')
            convert_dates(doc)
            self.docs.append(doc)

    def __getitem__(self, key):
        return self.docs[key]

    def first(self):
        """Get first doc."""
        return self.docs[0] if self.docs else None

    def count(self):
        """Get hits count."""
        return int(self.hits['hits']['total'])

    def info(self, response):
        """Add additional info to response."""
        if 'facets' in self.hits:
            response['_facets'] = self.hits['facets']

class Elastic(DataLayer):
    """ElasticSearch data layer."""

    serializers = {
        'integer': int,
        'datetime': parse_date
    }

    def init_app(self, app):
        app.config.setdefault('ELASTICSEARCH_URL', 'http://localhost:9200/')
        app.config.setdefault('ELASTICSEARCH_INDEX', 'eve')
        self.es = app.extensions['elasticsearch'] = ElasticSearch(app.config['ELASTICSEARCH_URL'])
        self.index = app.config['ELASTICSEARCH_INDEX']

        try:
            self.es.create_index(self.index)
        except IndexAlreadyExistsError:
            pass

    def find(self, resource, req):
        query = {
            'query': {
                'query_string': {
                    'query': request.args.get('q', '*'),
                    'default_field': request.args.get('df', '_all'),
                    'default_operator': 'AND'
                }
            }
        }

        if not req.sort and self._default_sort(resource):
            req.sort = self._default_sort(resource)

        # skip sorting when there is a query to use score
        if req.sort and 'q' not in request.args:
            query['sort'] = []
            sort = ast.literal_eval(req.sort)
            for (key, sortdir) in sort:
                query['sort'].append(dict([(key, 'asc' if sortdir > 0 else 'desc')]))

        if req.where:
            where = json.loads(req.where)
            if where:
                query['filter'] = {
                    'term': where
                }

        if req.max_results:
            query['size'] = req.max_results

        if req.page > 1:
            query['from'] = (req.page - 1) * req.max_results

        source_config = config.SOURCES[resource]
        if 'facets' in source_config:
            query['facets'] = source_config['facets']

        try:
            return self._parse_hits(self.es.search(query, index=self.index, doc_type=self._doc_type(resource), es_fields=self._fields(resource)))
        except ElasticHttpError:
            return ElasticCursor()

    def find_one(self, resource, **lookup):
        args = {
            'index': self.index,
            'doc_type': self._doc_type(resource),
            'es_fields': self._fields(resource),
        }

        if config.ID_FIELD in lookup:
            try:
                hit = self.es.get(id=lookup[config.ID_FIELD], **args)
            except ElasticHttpNotFoundError:
                return

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
                args['size'] = 1
                docs = self._parse_hits(self.es.search(query, **args))
                return docs.first()
            except ElasticHttpNotFoundError:
                return None

    def find_list_of_ids(self, resource, ids, client_projection=None):
        return self._parse_hits(self.es.multi_get(ids, self.index, self._doc_type(resource), self._fields(resource)))

    def insert(self, resource, doc_or_docs, **kwargs):
        ids = []
        doc_type = self._doc_type(resource)
        for doc in doc_or_docs:
            doc.update(self.es.index(self.index, doc_type, doc, id=doc.get('_id'), **kwargs))
            ids.append(doc['_id'])
        self.es.refresh(self.index)
        return ids

    def update(self, resource, id_, updates):
        return self.es.update(self.index, self._doc_type(resource), id=id_, doc=updates, refresh=True)

    def replace(self, resource, id_, document):
        return self.es.index(self.index, self._doc_type(resource), document, id=id_, overwrite_existing=True, refresh=True)

    def remove(self, resource, id_=None):
        if id_:
            return self.es.delete(self.index, self._doc_type(resource), id=id_, refresh=True)
        else:
            try:
                return self.es.delete_all(self.index, self._doc_type(resource), refresh=True)
            except ElasticHttpNotFoundError:
                return

    def _parse_hits(self, hits):
        """Parse hits response into documents."""
        return ElasticCursor(hits)

    def _doc_type(self, resource):
        """Get document type for given resource."""
        datasource = self._datasource(resource)
        return datasource[0]

    def _fields(self, resource):
        """Get projection fields for given resource."""
        datasource = self._datasource(resource)
        keys = datasource[2].keys()
        return ','.join(keys)

    def _default_sort(self, resource):
        datasource = self._datasource(resource)
        return datasource[3]
