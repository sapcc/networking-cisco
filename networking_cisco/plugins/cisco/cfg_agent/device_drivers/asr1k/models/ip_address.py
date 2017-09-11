class IpAddress(object):

    def __init__(self, ip, netmask=None):
        self._ip = ip
        self._netmask = netmask

    @property
    def ip(self):
        return self._ip

    @property
    def netmask(self):
        return self._netmask

    def __repr__(self):
        return "<{} {} {}>".format(self.__class__.__name__, self.ip,self.netmask)
