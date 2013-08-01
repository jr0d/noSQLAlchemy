import unittest

from nosqlalchemy import (
    Collection,
    Key,
    ListCollection,
    SubCollection,
    MongoDBInterface,
    MongoSession,
    ObjectId,
    LazyCollection
)

mdi = MongoDBInterface()
MSession = MongoSession(mdi)


class XSubCollection(SubCollection):
    x_item1 = Key()
    x_item2 = Key()


class SubCollectionList(ListCollection):
    __list_element_type__ = XSubCollection


class TempSubCollection(SubCollection):
    subkey1 = Key()
    subkey2 = Key()


class TempListCollection(ListCollection):
    __list_element_type__ = int


class LazySubCollection(SubCollection):
    module_name = Key()
    lazy_1 = LazyCollection()
    lazy_2 = LazyCollection()


class TempCollection(Collection):
    __name__ = 'tempdb'
    __database__ = 'charlie'
    __primary_key__ = 'test_key_1'

    test_key_1 = Key()
    test_key_2 = Key()
    test_key_3 = Key()
    update_key1 = Key()
    sub_collection = TempSubCollection()
    list_collection = TempListCollection()
    sub_collection_list = SubCollectionList()
    lazy_collection = LazyCollection()
    lazy_sub_collection = LazySubCollection()



    @classmethod
    def get_by_oid(cls, oid):
        if isinstance(oid, (str, unicode)):
            oid = ObjectId(oid)
        if not isinstance(oid, ObjectId):
            raise ValueError('Invalid ObjectID')

        return MSession.query(cls).find_one({'_id': oid})


class TestNoSQL(unittest.TestCase):
    oid = None
    key1_value = 'TestKey1'
    key2_value = 'TestKey2'
    key3_value = 'TestKey3'

    def setUp(self):
        MSession.drop_all(TempCollection)
        tc = TempCollection()
        tc.test_key_1 = self.key1_value
        tc.test_key_2 = self.key2_value
        tc.test_key_3 = self.key3_value
        tc.update_key1 = 0b1010011010

        self.oid = MSession.add(tc)

    def test_mongo_create(self):
        self.assertTrue(isinstance(self.oid, ObjectId),
                        'Got incorrect type for OID, %s' % type(self.oid))

    def test_mongo_get(self):
        tc = TempCollection.get_by_oid(self.oid)
        self.assertEqual(tc.test_key_1, self.key1_value,
                         'Get by attribute fails')
        self.assertEqual(tc['test_key_2'], self.key2_value,
                         'Get by item fails')

    def test_mongo_update(self):
        tc = TempCollection.get_by_oid(self.oid)
        tc.update_key1 += 0b1101111
        MSession.save(tc)
        tc = TempCollection.get_by_oid(self.oid)
        self.assertEqual(tc.update_key1, 777,
                         'Update failed, value is %d' % tc.update_key1)

    def test_sub_collection(self):
        tc = TempCollection.get_by_oid(self.oid)
        tsc = TempSubCollection()
        tsc.subkey1 = 'Subkey_1'
        tsc['subkey2'] = 'Subkey_2'
        tc.sub_collection = tsc
        MSession.save(tc)
        tc = TempCollection.get_by_oid(self.oid)
        self.assertEqual(tc.sub_collection['subkey1'], 'Subkey_1')
        self.assertEqual(tc.sub_collection.subkey2, 'Subkey_2')
        self.assertTrue(isinstance(tc.sub_collection, TempSubCollection))

    def test_list_collection(self):
        tc = TempCollection.get_by_oid(self.oid)
        li = [1, 2, 3]

        tc.list_collection.append(1)
        tc.list_collection.append(2)
        tc.list_collection.append(3)

        MSession.save(tc)
        tc = TempCollection.get_by_oid(self.oid)

        self.assertEqual(tc.list_collection, li)
        tc.list_collection.pop()
        li.pop()
        self.assertEqual(tc.list_collection, li)
        self.assertRaises(ValueError, tc.list_collection.append, 'I am string')

    def test_sub_collection_list(self):
        sub_collection = XSubCollection()
        sub_collection.x_item1 = 'One'
        sub_collection.x_item2 = 2

        tc = TempCollection.get_by_oid(self.oid)

        tc.sub_collection_list = sub_collection

        MSession.save(tc)

        tc = TempCollection.get_by_oid(self.oid)
        self.assertTrue(isinstance(tc.sub_collection_list, ListCollection))
        self.assertTrue(isinstance(tc.sub_collection_list[0], XSubCollection))
        self.assertEqual(tc.sub_collection_list[0]['x_item1'], 'One')
        self.assertEqual(tc.sub_collection_list[0].x_item2, 2)

    def test_lazy_collection(self):
        tc = TempCollection.get_by_oid(self.oid)
        tc.lazy_collection.str_1 = 'Something1'
        tc.lazy_collection.num_1 = 4
        tc.lazy_collection.dict_1 = {'1': 2}
        tc.lazy_collection.list_1 = [1, 2, 3]
        tc.lazy_sub_collection.module_name = 'My module'
        tc.lazy_sub_collection.lazy_1.key1 = {'1': 2}
        tc.lazy_sub_collection.lazy_2.key2 = 'Lazy2'
        MSession.save(tc)

        tc = TempCollection.get_by_oid(self.oid)
        self.assertEqual(tc.lazy_collection.str_1, 'Something1')
        self.assertEquals(tc.lazy_collection.num_1, 4)
        self.assertEquals(tc.lazy_collection.dict_1, {'1': 2})
        self.assertEquals(tc.lazy_collection['list_1'], [1, 2, 3])

        self.assertEqual(tc.lazy_sub_collection.module_name, 'My module')
        self.assertEqual(tc.lazy_sub_collection.lazy_1.key1, {'1': 2})
        self.assertEqual(tc.lazy_sub_collection.lazy_2.key2, 'Lazy2')


    def test_mongo_remove(self):
        tc = TempCollection()
        tc.test_key_1 = 'Tell Tale Heart'
        tc.test_key_2 = 'The Fall of the House of Usher'
        tc.test_key_3 = 'The Gold Bug'
        tc.update_key1 = 'The Cask Amontillado'

        new_oid = MSession.add(tc)

        tc = TempCollection.get_by_oid(new_oid)
        self.assertIsNotNone(tc, 'MSession.add failed')
        self.assertEqual(tc['test_key_1'], 'Tell Tale Heart', 'Bad value')
        MSession.remove(tc)

        self.assertIsNone(
            MSession.query(
                TempCollection).find_one({'test_key_3': 'The Gold Bug'}),
            'Object is still present')

    def test_mongo_misc(self):
        tc = TempCollection.get_by_oid(self.oid)
        enc_safe = tc.json_encode()
        self.assertEqual(enc_safe['_id'], str(self.oid))

        unicode(tc)
        str(tc)
        tc.__repr__()

        self.assertTrue(tc.present())

    def test_mongo_query(self):
        collections = list(MSession.query(TempCollection).all())
        self.assertTrue(len(collections) > 0)
        self.assertEqual(len(list(MSession.query(TempCollection).find(
            {'test_key_1': self.key1_value}))), 1)
        self.assertIsNone(MSession.query(TempCollection).find_one(
            {'test_key1': 'something'}))
        self.assertTrue(MSession.query(TempCollection).count() >= 1)
        self.assertEqual(MSession.query(TempCollection).count({'_id': self.oid}), 1)

    def test_raw_mdi(self):
        cdb = mdi.get_database('charlie')
        col = mdi.get_collection(cdb, 'tempdb')
        self.assertIsNotNone(col, 'Could not grab raw collection')

    def test_bulk_remove(self):
        for x in xrange(10):
            tc = TempCollection()
            tc.test_key_1 = str(x)
            tc.test_key_2 = 'nerf'
            MSession.save(tc)
        tcs = list(MSession.query(TempCollection).find(dict(test_key_2='nerf')))
        self.assertEqual(len(tcs), 10)
        MSession.query(TempCollection).remove(dict(test_key_2='nerf'))
        tcs = list(MSession.query(TempCollection).find(dict(test_key_2='nerf')))
        self.assertEqual(len(tcs), 0)

    def tearDown(self):
        tc = TempCollection.get_by_oid(self.oid)
        tc.remove()
        MSession.drop_all(TempCollection)
        self.assertIsNone(TempCollection.get_by_oid(self.oid),
                          'Something is still present')
