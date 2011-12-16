''' 
Author: Jared Rodriguez
Copyright 2011, Jared Rodriguez

License: GPLv2
email: jared@blacknode.net
about: This is mostly a joke, but is actually being used in a
production environment.
'''

from datetime import datetime
from pymongo import Connection


class MongoSession(object):
    def __init__(self, mdi=None):
        self.connection = mdi.connection

    def _get_collection_from_object(self, collection_obj):
        database = self.connection[collection_obj.__database__]
        return database[collection_obj.__name__]

    def query(self, collection_cls=None, **kw):
## TODO, verification of collection_cls. __mro__ ? 
        return Mquery(self.connection, collection_cls)

    def add(self, collection_obj):
        database = self.connection[collection_obj.__database__]
        collection = database[collection_obj.__name__]
        return collection.insert(collection_obj)

    def save(self, collection_obj):
        database = self.connection[collection_obj.__database__]
        collection = database[collection_obj.__name__]
        collection.save(collection_obj)

    def remove(self, collection_obj):
        collection = self._get_collection_from_object(collection_obj)
        collection.remove(collection_obj)

    def drop_all(self, collection_cls):
        collection = self._get_collection_from_object(collection_cls())
        collection.remove({})


class Mquery(object):
    def __init__(self, connection, col):
        self.connection = connection
        self.col = col
        self.col_name = self.col().__name__
        self.database_name = self.col.__database__
        self.database = self.connection[self.database_name]
        self.collection = self.database[self.col_name]

    def all(self, json_safe=False):
        '''
        generator of baked Collection objects.
        '''
        for item in self.collection.find():
            inst = self.col()
            for key in inst.__keys__:
                inst[key] = item[key]
            if json_safe:
                inst['_id'] = str(inst['_id'])
            yield inst

    def find_one(self, kw):
        data = self.collection.find_one(kw)
        if data:
            return self.col(self.database, **data)
        return None

    def find(self, kw):
        data = self.collection.find(kw)
        for item in data:
            inst = self.col(self.database, **item)
            yield inst

    def count(self, kw=None):
        if not kw:
            return self.collection.count()
        return self.collection.find(kw).count()

class MongoDBInterface(object):
    '''
    pymongo bindings interface.
    '''
    def __init__(self, ip='127.0.0.1', port=27017):
        self.connection = Connection(ip, port)

    def get_database(self, database):
        return self.connection[database]

    def get_collection(self, database, collection):
        return database[collection]

def commit(collection_obj):
    return collection_obj.collection.insert(collection_obj)

class Key(object):
    '''
    Represents a key value. Will be used in the future to provide type
    safty and schema varification. Right now it is used as a simple way
    to identify class variables for declarative collection defintion. 

    Subclass type?
    '''

    def __init__(self, data_type='no_type'):
        self.data_type = data_type
        self.data = None

    def __unicode__(self):
        return unicode(self.data)

    def __repr__(self):
        return self.__unicode__()


class Collection(dict):
    '''
    I would like to be able to define collections declarativly.
    Because pymongo takes dictionaries, Collection subclasses dict.
    The user will work with the object members as attributes.
    These attributes, exposed and defined by psuedo-class vars,
    are transparently converted to dictionary keys and values. 

    early example of how this might work:

    class User(Collection):
        __name__ = 'kerror'

        user = Key('no_type')
        email = Key('no_type')

    The class variables are extracted durring __init__ and added to the
    __keys__ class variable. Subsequent __getattr__ and __setattr__ calls
    with attribute keys matching definition keys, set the dictionary values.

    As the object can easily be coerced to dict() it can be passed directly
    to pymongo methods. This allows for declaritve model definitions,
    attribute style intefaces, logical accessors to the collection through
    the class interface, and provides a drop in replacement for older code
    using dictionary base classes.
    '''
    __name__ = None
    __database__ = None 
    __keys__ =  list()
    _id = Key()

    def __init__(self, session=None, **kwargs):
        super(dict, self).__init__()
        self.__keys__ = ['_id']
        self.session = session
        self.database = None
        self.collection = None

        if self.session:
            self.connection = self.session.connection
            self.database = self.connection[self.__database__]
            self.collection = self.database[self.__name__]

        for name, obj in vars(self.__class__).items():
            if isinstance(obj, Key):
                self.__keys__.append(name)
                self[name] = obj.data

        for key in kwargs.keys():
            if key in self.__keys__:
                self[key] = kwargs[key]
                obj = getattr(self, key)
                obj.data = self[key]


    def __setattr__(self, item, value):
        obj = getattr(self, item, None)
        #print 'In setattr: ' + str(type(obj)) + ' item name: ' + str(item)
        if isinstance(obj, Key):
            obj.__setattr__('data', value)
            self[item] = obj.data
        else:
            dict.__setattr__(self, item, value)

    def remove(self):
        self.collection.remove(self)

    def present(self):
        return self.collection.find_one(self) > 0

    def __unicode__(self):
        out = unicode(self.__name__) + u' Object: \n'
        for k in self.__keys__:
            out = out + u'    %s => %s\n' % (k, self.get(k))
        return out + '\n'

    def __str__(self):
        return str(self.__unicode__())

    def __repr__(self):
        return self.__unicode__()

    def json_encode(self):
        temp = dict(self)
        if temp.has_key('_id'):
            temp['_id'] = str(temp['_id'])
        return temp
