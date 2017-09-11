class Vrf(object):
    def __init__(self):
        super(Vrf, self).__init__()
        self.id = None
        self.interfaces = []
        self.gateway = None

    def __repr__(self):
        return "<{} {} {} {}>".format(self.__class__.__name__, self.id,self.interfaces,self.gateway)