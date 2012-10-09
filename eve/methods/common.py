from flask import current_app as app
from flask import abort
from ast import literal_eval
from eve.utils import str_to_date, parse_request, document_etag


def get_document(resource, **lookup):

    req = parse_request()
    document = app.data.find_one(resource, **lookup)
    if document:
        if not req.if_match:
            # we don't allow editing unless the client provides an etag
            # for the document
            abort(403)
        if req.if_match != document_etag(document):
            # client and server etags must match, or we don't allow editing
            # (ensures that client's version of the document is up to date)
            abort(412)

    return document


def parse(value, resource):

    document = literal_eval(value)

    schema_dates = app.config['DOMAIN'][resource]['dates']
    document_dates = schema_dates.intersection(set(document.keys()))
    for date_field in document_dates:
        document[date_field] = str_to_date(document[date_field])

    return document
