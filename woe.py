from nosqlalchemy import Collection, Key

class Inventory(Collection):
    __name__ = 'mac_store'
    __database__ = 'kserver'
    __primary_key__ = 'mac_address'

    mac_address = Key()
    server_number = Key()
    client_ip = Key()
    status = Key()
    ip_info = Key()
    private_key = Key()
    client_interface = Key()
    time_created = Key()
    time_updated = Key()
    control_port = Key()
    kick_id = Key()
    kick_token = Key()


data = {u'status': {u'msg': u'Deadly', u'color': u'red'}, u'ip_info': None, u'server_number': None, u'client_interface': u'eth0', u'client_ip': u'127.0.0.1', u'control_port': 5000, u'mac_address': u'00:00:FF:11:22:AF'}

inv = Inventory()

print inv
print Inventory(**data)
print 'should be cleared!\n\n\n\n'
print Inventory()

