
from pyelasticsearch import ElasticSearch
from eve.io.base import DataLayer, ConnectionException
from eve.utils import config

class Elastic(DataLayer):

    def init_app(self, app):
        app.config.setdefault('ELASTICSEARCH_URL', 'http://localhost:9200/')
        app.config.setdefault('ELASTICSEARCH_INDEX', 'eve')
        self.es = app.extensions['elasticsearch'] = ElasticSearch(app.config['ELASTICSEARCH_URL'])

    def find(self, resource, req):
        args = dict()

        if req.max_results:
            args['size'] = req.max_results

        if req.page > 1:
            args['es_from'] = (req.page - 1) * req.max_results

        if req.where:
            args['query'] = req.where

        datasource, filter_, projection = self._datasource_ex(resource)

        args['index'] = app.config['ELASTICSEARCH_INDEX']
        args['doc_type'] = datasource

        return self.es.search(**args)

    def find_one(self, resource, **lookup):
        datasource, filter_, projection = self._datasource_ex(resource, lookup)
        return self.es.get(app.config['ELASTICSEARCH_INDEX'], datasource, id=lookup[config.ID_FIELD], fields=projection)


    def find_list_of_ids(self, resource, ids, client_projection=None):
        datasource, filter_, fields = self._datasource_ex(resource)
        return self.es.multi_get(ids, app.config['ELASTICSEARCH_INDEX'], dataresource, fields)

    def insert(self, resource, doc_or_docs):
        datasource, filter_, _ = self._datasource_ex(resource)

        for doc in doc_or_docs:
            self.es.index(app.config['ELASTICSEARCH_INDEX'], datasource, doc)
        self.es.refresh(app.config['ELASTICSEARCH_INDEX'])
        return doc_or_docs

    def update(self, resource, id_, updates):
        datasource, filter_, _ = self._datasource_ex(resource)
        return self.es.update(app.config['ELASTICSEARCH_INDEX'], datasource, id_, updates, refresh=True)

    def replace(self, resource, id_, document):
        datasource, filter_, _ = self._datasource_ex(resource)
        return self.es.index(app.config['ELASTICSEARCH_INDEX'], datasource, doc, id=id_, overwrite_existing=True, refresh=True)

    def remove(self, resource, id_=None):
        datasource, filter_, _ = self._datasource_ex(resource)
        if id_:
            return self.es.delete(app.config['ELASTICSEARCH_INDEX'], datasource, id=id_, refresh=True)
        else:
            return self.es.delete_all(app.config['ELASTICSEARCH_INDEX'], datasource, refresh=True)
