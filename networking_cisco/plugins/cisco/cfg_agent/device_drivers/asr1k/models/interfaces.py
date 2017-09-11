
class BaseInterface(object):
    def __init__(self):
        super(BaseInterface,self).__init__()
        self.parent_interface=""
        self.encapsulation = 0
        self.description = ""

        self.nat_mode = None
        self.primary_ip = None
        self.secondary_ips = []
        self.ha_info= None

    def __repr__(self):

        return "<{} {} {}>".format(self.__class__.__name__, self.parent_interface, self.encapsulation)


class InternalInterface(BaseInterface):
    def __init__(self):
        super(InternalInterface, self).__init__()



class GatewayInterface(BaseInterface):
    def __init__(self):
        super(GatewayInterface, self).__init__()

class HaInfo(object):
    def __init__(self):
        super(HaInfo, self).__init__()
