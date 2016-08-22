# This Python file uses the following encoding: utf-8
import codecs
import json
import cherrypy

import logging

from ZODB.FileStorage import FileStorage
from ZODB.DB import DB
from persistent.mapping import PersistentMapping
import transaction

logger = logging.getLogger('TagServer')
handler = logging.FileHandler('/home/cloud/var/log/tag_server.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class TagServer(object):

  def __init__(self):
    self.storage = FileStorage('data/tag_data.fs')
    self.db = DB(self.storage)
    self.connection = self.db.open()
    self.z = self.connection.root()

  @cherrypy.expose
  @cherrypy.tools.json_in()
  @cherrypy.tools.json_out()
  def default(self, namespace=None, keys=None, search=None):
    (GET, PUT, POST, DELETE) = ('GET', 'PUT', 'POST', 'DELETE')
    method = cherrypy.request.method
    if method == GET and namespace is None:
      logger.info('Listing namespaces')
      return self.z.keys()

    if method == GET and search is not None:
      logger.info('Listing keys in namespace [%s]' % namespace)
      return dict((k, list(v)) for k, v in self.z[namespace].items() if search in v)

    if keys is None:
      if namespace in self.z:
        logger.info('No key(s) provided; pulling all keys from namespace [%s]' % namespace)
        keys = self.z[namespace].keys()
      else:
        logger.info('No key(s) provided; namespace does not exist.')
        return {}
    else:
      keys = keys.split(',')

    if method in [PUT, POST]:
      logger.info('Handling P{UT,OST} request')
      json = cherrypy.request.json
      invalid = [x for x in json.keys() if x not in ['add', 'remove']]
      if (len(invalid) > 0):
        raise cherrypy.HTTPError("400 Bad Request", "Invalid JSON arguments specifiedi ([%s] received, [add,remove] expected)" % ','.join(invalid))
      if 'add' in json.keys() and isinstance(json['add'], list):
        if namespace not in self.z:
          self.z[namespace] = PersistentMapping()
        for key in keys:
          if key not in self.z[namespace]:
            self.z[namespace][key] = set([])
          self.z[namespace][key].update(json['add'])
        self.z[namespace]._p_changed = 1
      if 'remove' in json.keys() and isinstance(json['remove'], list):
        if namespace in self.z:
          for key in keys:
            for value in json['remove']:
              if value in self.z[namespace][key]:
                self.z[namespace][key].remove(value)
          self.z[namespace]._p_changed = 1
      transaction.commit()

    elif method == DELETE:
      logger.info('Handling DELETE request...')
      if namespace in self.z:
        for key in keys:
          if key in self.z[namespace]:
            del self.z[namespace][key]
        self.z[namespace]._p_changed = 1
        transaction.commit()
        if len(self.z[namespace]) == 0:
          del self.z[namespace]
          self.z._p_changed = 1
        transaction.commit()
      logger.info('...DELETE request handled')
      return {}

    # For all other cases, return the new or unchanged state of the list:
    if namespace not in self.z:
      logger.info('Handling GET request; namespace [%s] not found' % namespace)
      return {}
    logger.info('Handling GET request...')
    throw_away = {}
    for key in keys:
      if key in self.z[namespace]:
        throw_away[key] = list(self.z[namespace][key])
    logger.info('...GET request handled')
    return throw_away

  class TagClient:
    def __init__(self, url, namespace='default'):
      self._URL = url
      self._namespace = namespace

    def get(self, keys):
      return requests.get(self._URL + self._namespace + '/' + ','.join(keys), verify=False).json()

    def add(self, keys, values):
      headers = {'Content-Type': 'application/json'}
      return requests.post(self._URL + self._namespace + '/' + ','.join(keys), data = json.dumps({'add': values}), headers=headers, verify=False).json()

    def remove(self, keys, values):
      headers = {'Content-Type': 'application/json'}
      return requests.post(self._URL + self._namespace + '/' + ','.join(keys), data = json.dumps({'remove': values}), headers=headers, verify=False).json()

    def search(self, value):
      return requests.get(self._URL + self._namespace + '/', params={'search': value}, verify=False).json()

    def delete(self, keys):
      return requests.delete(self._URL + self._namespace + '/' + ','.join(keys), verify=False).json()    
