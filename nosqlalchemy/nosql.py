import time
from bson.objectid import ObjectId
from pymongo import MongoClient, MongoReplicaSetClient


__all__ = [
    'MongoSession',
    'Key',
    'Collection',
    'SubCollection',
    'ListCollection',
    'ObjectId',
    'LazyCollection',
    'MongoDBConnection'
]


class MongoSession(object):
    def __init__(self, client=None):
        self.connection = client.connection

    def _get_collection_from_object(self, collection_obj):
        database = self.connection[collection_obj.__database__]
        return database[collection_obj.__collection_name__]

    def query(self, collection_cls=None):
    ## TODO, verification of collection_cls. __mro__ ?
        return Mquery(self.connection, collection_cls)

    def add(self, collection_obj):
        database = self.connection[collection_obj.__database__]
        collection = database[collection_obj.__collection_name__]
        now = time.time()
        collection_obj.time_created = now
        collection_obj.time_updated = now
        return collection.insert(collection_obj)

    def save(self, collection_obj):
        database = self.connection[collection_obj.__database__]
        collection = database[collection_obj.__collection_name__]
        now = time.time()
        # Possible bug, we would never try to save time_created
        if not collection_obj.time_created:
            collection_obj.time_created = now
        collection_obj.time_updated = now
        return collection.save(collection_obj)

    def remove(self, collection_obj):
        collection = self._get_collection_from_object(collection_obj)
        collection.remove({'_id': collection_obj._id})

    def drop_all(self, collection_cls):
        collection = self._get_collection_from_object(collection_cls())
        collection.remove({})

    def update(self, collection_cls, update_spec, update_data, multi=False):
        collection = self._get_collection_from_object(collection_cls)
        update_data.update(dict(time_updated=time.time()))
        return collection.update(update_spec, {'$set': update_data}, multi=multi)

class Mquery(object):
    def __init__(self, connection, col):
        self.connection = connection
        self.col = col
        self.col_name = self.col().__collection_name__
        self.database_name = self.col.__database__
        self.database = self.connection[self.database_name]
        self.collection = self.database[self.col_name]

    def all(self):
        """
        generator of baked Collection objects.
        """
        for item in self.collection.find():
            inst = self.col(self.database, **item)
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

    def remove(self, kw):
        return self.collection.remove(kw)

    def count(self, kw=None):
        if not kw:
            return self.collection.count()
        return self.collection.find(kw).count()


class MongoDBConnection(object):
    """
    pymongo bindings interface.
    """

    def __init__(self, host_or_url='127.0.0.1:27017', replica_set='', **kwargs):
        if replica_set:
            self.connection = MongoReplicaSetClient(host_or_url, replicaSet=replica_set, **kwargs)
        else:
            self.connection = MongoClient(host_or_url, **kwargs)

    def get_database(self, database):
        return self.connection[database]


class Key(object):
    """
    A base key object.

    Key should be used by type subclasses as a base type. This will allow us
    to enforce a small amount of type safety, for instance:

    Integer(Key):
      python_type = int

    Col(Collection):
      number = Integer()

    on __setattr__ Collection would perform an isinstance against the user
    supplied value.
    """

    def __init__(self, default=None, data_type='no_type'):
        self.data_type = data_type
        self.data = None
        self.default = default

class LazyCollection(dict):
    """
    A dictionary type implementing attribute style value access.
    """
    def __init__(self, **kwargs):
        super(LazyCollection, self).__init__(kwargs)
        for k, v in self.items():
            object.__setattr__(self, k, v)

    def __setattr__(self, key, value):
        self[key] = value
        object.__setattr__(self, key, value)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        object.__setattr__(self, key, value)


class SubCollectionMeta(dict):
    __keys__ = list()

    def __new__(cls, *args, **kwargs):
        obj = super(SubCollectionMeta, cls).__new__(cls)
        obj.__keys__ = list()
        return obj


class SubCollection(SubCollectionMeta):
    def __init__(self, **kwargs):
        super(SubCollection, self).__init__()

        for name, obj in self.__class__.__dict__.items():
            if isinstance(obj, Key):
                self.__keys__.append(name)
                self[name] = obj.default
                object.__setattr__(self, name, obj.default)
            if isinstance(obj, (ListCollection, LazyCollection)):
                self.__keys__.append(name)
                self[name] = obj.__class__()

        for key in kwargs.keys():
            if key in self.__keys__:
                if isinstance(self[key], LazyCollection):
                    self[key] = self[key].__class__(**kwargs[key])
                elif isinstance(self.get(key), ListCollection):
                    if not isinstance(kwargs[key], (ListCollection, list)):
                        raise ValueError(
                            'attempting to populate list %s with '
                            'non-list value, %s' % (key, str(kwargs[key])))
                    if self[key].__list_element_type__.__base__ in [SubCollection, LazyCollection, dict]:
                        for el in kwargs[key]:
                            self[key].append(self[key].__list_element_type__(**el))
                    else:
                        self[key] = self[key].__class__(kwargs[key])
                else:
                    self[key] = kwargs[key]
                object.__setattr__(self, key, self[key])

    def __setattr__(self, item, value):
        if item in self.__keys__:
            self[item] = value
        object.__setattr__(self, item, value)


class ListCollection(list):
    __list_element_type__ = object

    def append(self, obj):
        if not isinstance(obj, self.__list_element_type__):
            raise ValueError('Invalid type added to list.')
        list.append(self, obj)


class CollectionInstanceException(Exception):
    pass


class CollectionMeta(dict):
    __keys__ = list()
    _id = Key()
    time_created = Key()
    time_updated = Key()

    def __new__(cls, *args, **kwargs):
        obj = super(CollectionMeta, cls).__new__(cls)
        obj.__keys__ = ['_id', 'time_created', 'time_updated']
        for key in obj.__keys__:
            if not key == '_id':
                obj[key] = None
        return obj


class Collection(CollectionMeta):
    """
    I would like to be able to define collections declaratively.
    Because pymongo takes dictionaries, Collection subclasses dict.
    The user will work with the object members as attributes.
    These attributes, exposed and defined by psuedo-class vars,
    are transparently converted to dictionary keys and values.

    early example of how this might work:

    class User(Collection):
        __collection_name__ = 'kerror'

        user = Key('no_type')
        email = Key('no_type')

    The class variables are extracted during __init__ and added to the
    __keys__ class variable. Subsequent __setattr__ calls with attribute
    keys matching definition keys, set the dictionary values.

    As the object can easily be coerced to dict() it can be passed directly
    to pymongo methods. This allows for declarative model definitions,
    attribute style interfaces, logical accessors to the collection through
    the class interface, and provides a drop in replacement for older code
    using dictionary base classes.
    """
    __collection_name__ = None
    __database__ = None

    def __init__(self, session=None, **kwargs):
        super(Collection, self).__init__()
        self.session = session
        self.database = None
        self.collection = None

        if self.session:
            self.connection = self.session.connection
            self.database = self.connection[self.__database__]
            self.collection = self.database[self.__collection_name__]

        self._build(kwargs)
        self.__setitem__ = self.__setitem_after_init__

    def _build(self, kwargs):
        # load keys from class variables
        for name, obj in self.__class__.__dict__.items():
            if isinstance(obj, Key):
                self.__keys__.append(name)
                self[name] = obj.default
                object.__setattr__(self, name, obj.default)
            if isinstance(obj, (SubCollection, ListCollection, LazyCollection)):
                self.__keys__.append(name)
                self[name] = obj.__class__()
                object.__setattr__(self, name, obj.__class__())

        for key in kwargs.keys():
            if key in self.__keys__:
                if isinstance(self.get(key), SubCollection):
                    if isinstance(kwargs[key], (SubCollection, dict)):
                        self[key] = self[key].__class__(**kwargs[key])
                    else:
                        self[key] = self[key].__class__()
                elif isinstance(self.get(key), LazyCollection):
                    self[key] = self[key].__class__(**kwargs[key])
                elif isinstance(self.get(key), ListCollection):
                    if not isinstance(kwargs[key], (ListCollection, list)):
                        raise ValueError(
                            'attempting to populate list %s with '
                            'non-list value, %s' % (key, str(kwargs[key])))
                    if self[key].__list_element_type__.__base__ in [SubCollection, LazyCollection, dict]:
                        for el in kwargs[key]:
                            self[key].append(self[key].__list_element_type__(**el))
                    else:
                        self[key] = self[key].__class__(kwargs[key])
                else:
                    self[key] = kwargs[key]
                object.__setattr__(self, key, self[key])

    def __setattr__(self, attr, value):
        if attr in self.__keys__:
            if isinstance(self[attr], SubCollection):
                for subitem in self[attr].__keys__:
                    setattr(self[attr], subitem, value[subitem])
            if isinstance(self[attr], (ListCollection, list)):
                if not isinstance(value, (ListCollection, list)):
                    self[attr].append(value)
                else:
                    self[attr] += value
                value = self[attr]
            self[attr] = value
        object.__setattr__(self, attr, value)

    def __setitem_after_init__(self, key, value):
        object.__setattr__(self, key, value)
        dict.__setitem__(self, key, value)

    def remove(self):
        self.collection.remove(self['_id'])

    def present(self):
        return self.collection.find_one(self) > 0

    def __unicode__(self):
        out = unicode(self.__collection_name__) + u' Object: \n'
        for k in self.__keys__:
            out += u'    %s => %s\n' % (k, self.get(k))
        return out + '\n'

    def __str__(self):
        return str(self.__unicode__())

    def __repr__(self):
        return self.__unicode__()

    @property
    def object_id(self):
        if not isinstance(self._id, ObjectId):
            return None
        return self._id

    def collection_update(self, update_data):
        if not self.object_id:
            raise CollectionInstanceException('This instance is not mapped to an object_id.')
        spec = dict(_id=self.object_id)
        update_data.update(dict(time_updated=time.time()))
        self.collection.update(spec, {'$set': update_data})
        data = self.collection.find_one(spec)
        self.__init__(self.session, **data)
