
import re
import xml.etree.ElementTree as ET
from networking_cisco.plugins.cisco.common.htparser import HTParser
#from networking_cisco.plugins.cisco.l3.drivers.asr1k import asr1k_routertype_driver as routertype
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k.validator import test_config

from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k.models import (ip_address, vrf, asr1k_device_config_parser)



N_ROUTER_PREFIX = "nrouter-"#routertype.N_ROUTER_PREFIX

class BaseObject(object):
    def __init__(self,object_config,full_config):
        self.full_config = full_config
        self.object_config = object_config

    def match(self, regex, text=None,group=1):
        if text is None:
            text =self.object_config.text

        match_obj = re.match(regex, text)
        if(match_obj):
            return match_obj.group(group)

    def match_one(self, regex, group=1):
        stansa = self.object_config.re_search_children(regex)
        if len(stansa) == 1:
            return self.match(regex, stansa[0].text,group=group)

        else:
            return


class BaseInterface(BaseObject):

    INTF_REGEX = "interface \S+\.(\d+)"
    INTF_DESC_REGEX = "\s*description (OPENSTACK_NEUTRON_INTF|OPENSTACK_NEUTRON_EXTERNAL_INTF)"
    INTF_EXT_DESC_REGEX = "\s*description (OPENSTACK_NEUTRON_EXTERNAL_INTF)"
    INTF_V4_ADDR_REGEX = "\s*ip address (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$"
    INTF_V4_SECONDARY_ADDR_REGEX = "\s*ip address (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) secondary$"
    HSRP_V4_VIP_REGEX = "\s*standby (\d+) ip (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$"
    HSRP_V4_SECONDARY_VIP_REGEX = "\s*standby (\d+) ip (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) secondary$"
    HSRP_PRIORITY_REGEX = "\s*standby (\d+) priority (\d+)"
    HSRP_GROUP_REGEX = "\s*standby (\d+) name neutron-hsrp-(\d+)-(\d+)"
    INTF_NAT_REGEX = "\s*ip nat (inside|outside)"

    def __init__(self,object_config,full_config):

        super(BaseInterface, self).__init__(object_config,full_config)

        self.encapsulation = self.match(BaseInterface.INTF_REGEX)
        self.description = self.match_one(BaseInterface.INTF_DESC_REGEX)

        self.nat_mode = self.match_one(BaseInterface.INTF_NAT_REGEX)
        self.primary_ip = self.__get_primary_ip(BaseInterface.INTF_V4_ADDR_REGEX)
        self.secondary_ips= self.__get_secondary_ips(BaseInterface.INTF_V4_SECONDARY_ADDR_REGEX)
        self.standby= StandbyInfo(self.object_config,self.full_config)

    def __get_primary_ip(self,regex):
        return ip_address.IpAddress(self.match_one(regex),self.match_one(regex,2))

    def __get_secondary_ips(self,regex):
        result =[]
        stansas = self.object_config.re_search_children(regex)
        for stansa in stansas:
            result.append(ip_address.IpAddress(self.match(regex,stansa.text,1),self.match(regex,stansa.text,2)))
        return result

    def __repr__(self):
        return '''
                  <{}
                   {}
                   {}
                   {}
                   {}
                   {}
                   {}>
                   '''.format(self.__class__.__name__, self.object_config,self.encapsulation, self.primary_ip, self.secondary_ips,self.nat_mode,self.standby)


class StandbyInfo(BaseObject):
    def __init__(self, object_config, full_config):
        super(StandbyInfo, self).__init__(object_config,full_config)
        self.id = self.match_one(BaseInterface.HSRP_GROUP_REGEX,group=2)
        self.encapsulation = self.match_one(BaseInterface.HSRP_GROUP_REGEX,group=3)
        self.group = self.match_one(BaseInterface.HSRP_V4_VIP_REGEX)
        self.ip = self.__get_primary_ip(BaseInterface.HSRP_V4_VIP_REGEX)
        self.secondary_ips = self.__get_secondary_ips(BaseInterface.HSRP_V4_SECONDARY_VIP_REGEX)
        self.priority = self.match_one(BaseInterface.HSRP_PRIORITY_REGEX,group=2)



    def __get_primary_ip(self,regex):
        return ip_address.IpAddress(self.match_one(regex,group=2))

    def __get_secondary_ips(self,regex):
        result =[]
        stansas = self.object_config.re_search_children(regex)
        for stansa in stansas:
            result.append(ip_address.IpAddress(self.match(regex,stansa.text,group=2)))
        return result

    def __repr__(self):
        return '''
                  <{}
                   {}
                   {}
                   {}
                   {}
                   {}
                   {}
                   {}>
                   '''.format(self.__class__.__name__, self.object_config,self.group,self.ip, self.secondary_ips,self.priority,self.id,self.encapsulation)


class TenantVrf(BaseObject):

    NROUTER_REGEX = N_ROUTER_PREFIX + "(\w{6,6})"
    VRF_REGEX = "vrf definition " + NROUTER_REGEX

    @staticmethod
    def from_device_config(config):
        vrfs = []
        for vrf in config.find_objects(TenantVrf.VRF_REGEX):
            vrfs.append(TenantVrf(vrf, config ))

        return vrfs

    def __init__(self, object_config, full_config):
        super(TenantVrf, self).__init__(object_config,full_config)

        self.id = self.match(TenantVrf.VRF_REGEX)
        self.interface = self.__build_interface()
        self.global_interface = None #TODO based on HRSP
        self.static_nats = self.__build_static_nat()
        self.nat_overloads = self.__build_nat_overload()
        self.nat_pools = self.__build_nat_pools()

        self.default_route = self.__build_default_route()
        self.routes = self.__build_routes()
        self.access_lists = self.__build_access_lists()

    def __build_interface(self):
        return TenantInterface.from_device_config(self.id,self.full_config)

    def __build_static_nat(self):
        static_nat = []

        regex = StaticNat.SNAT_VRF_REGEX % (self.id)

        for object_config in self.full_config.find_objects(regex):
            static_nat.append(StaticNat(object_config,self.full_config))

        return static_nat

    def __build_nat_overload(self):
        nat_overload = []

        #regex = NatOverload.NAT_OVERLOAD_VRF_REGEX % (self.id)

        #for object_config in self.full_config.find_objects(regex):
        #    nat_overload.append(NatOverload(object_config,self.full_config))

        return nat_overload

    def __build_nat_pools(self):
        regex = NatPool.NAT_POOL_VRF_REGEX % (self.id)
        result=[]

        nat_pools = self.full_config.find_objects(regex)

        for nat_pool in nat_pools:
            result.append(NatPool(nat_pool,self.full_config))
        return result

    def __build_access_lists(self):
        if self.interface:
            regex = AccessList.ACCESS_LIST_VRF_REGEX % (self.interface.encapsulation)
            result=[]

            access_lists = self.full_config.find_objects(regex)

            for access_list in access_lists:
                result.append(AccessList(access_list,self.full_config))
            return result
        return[]


    def __build_default_route(self):
        regex = Route.DEFAULT_ROUTE_ROUTE_VRF_REGEX % (self.id)

        default_route = self.full_config.find_objects(regex)
        if len(default_route) == 1:
            return Route(default_route[0],self.full_config,True)
        else:
            print("No or Multiple default routes")
            return


    def __build_routes(self):
        regex = Route.TENANT_ROUTE_ROUTE_VRF_REGEX % (self.id)
        result = []
        routes = self.full_config.find_objects(regex)

        for route in routes:
            result.append(Route(route,self.full_config))

        return result

    def __repr__(self):
        return "<{} {} {} {} {} {} {} {} {}>".format(self.__class__.__name__, self.id,self.interface,self.static_nats,self.nat_pools,self.default_route,self.routes,self.access_lists,self.nat_overloads)



class TenantInterface(BaseInterface):

    VRF_INTF_REGEX_NEW = "\s*vrf forwarding " + TenantVrf.NROUTER_REGEX

    @staticmethod
    def from_device_config(vrf_id,config):
        vrf_name = N_ROUTER_PREFIX+vrf_id

        runcfg_intfs = [obj for obj in config.find_objects(TenantInterface.INTF_REGEX)
                        if obj.re_search_children(vrf_name)]

        if len(runcfg_intfs) == 1:
            interface_conf =  runcfg_intfs[0]
        else:
            print("VRF {} has no or multiple interfaces".format(vrf_id))
            return


        return TenantInterface(interface_conf, config )

    def __init__(self,object_config,full_config):
        super(TenantInterface, self).__init__(object_config,full_config)







class StaticNat(BaseObject):

    SNAT_GENERIC_REGEX = ("ip nat inside source static"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) vrf " +
    TenantVrf.NROUTER_REGEX +
    " redundancy neutron-hsrp-(\d+)-(\d+)")

    SNAT_VRF_REGEX = ("ip nat inside source static"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) vrf " +
    N_ROUTER_PREFIX +
    "%s redundancy neutron-hsrp-(\d+)-(\d+)")


    def __init__(self, object_config, full_config):
        super(StaticNat, self).__init__(object_config,full_config)
        self.local_ip =  ip_address.IpAddress(self.match_one(StaticNat.SNAT_GENERIC_REGEX,group=1))
        self.global_ip = ip_address.IpAddress(self.match_one(StaticNat.SNAT_GENERIC_REGEX,group=2))
        self.redundancy_group = self.match_one(StaticNat.SNAT_GENERIC_REGEX,group=4)
        self.redundancy_seg = self.match_one(StaticNat.SNAT_GENERIC_REGEX,group=5)


    def __repr__(self):
        return "<{} {} {} {} {}>".format(self.__class__.__name__, self.local_ip, self.global_ip, self.redundancy_group, self.redundancy_seg)

class NatPoolOverload(BaseObject):

    NAT_POOL_OVERLOAD_GENERIC_REGEX = ("ip nat inside source list"
    " neutron_acl_(\d+)_(\w{1,8}) pool " +
    TenantVrf.NROUTER_REGEX +
    "_nat_pool vrf " +
    TenantVrf.NROUTER_REGEX +
    " overload")


    NAT_POOL_OVERLOAD_VRF_REGEX = ("ip nat inside source list"
    " neutron_acl_(\d+)_(\w{1,8}) pool " +
    N_ROUTER_PREFIX +
    "%s_nat_pool vrf " +
    N_ROUTER_PREFIX +
    "%s overload")


    def __init__(self, object_config, full_config,vrf_id):
        super(NatPoolOverload, self).__init__(object_config,full_config)
        self.vrf_id = vrf_id
        self.acl_id = self.match_one(NatPoolOverload.NAT_POOL_OVERLOAD_GENERIC_REGEX,group=2)
        self.encapsulation = self.match_one(NatPoolOverload.NAT_POOL_OVERLOAD_GENERIC_REGEX,group=1)

    def __repr__(self):
        return "<{} {} {} {}>".format(self.__class__.__name__, self.vrf_id, self.acl_id,self.encapsulation)

class NatPool(BaseObject):

    NAT_POOL_GENERIC_REGEX = ("ip nat pool " +
    TenantVrf.NROUTER_REGEX +
    "_nat_pool (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) netmask"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")

    NAT_POOL_VRF_REGEX = ("ip nat pool " +
    N_ROUTER_PREFIX +
    "%s_nat_pool (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) netmask"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")

    def __init__(self, object_config, full_config):
        super(NatPool, self).__init__(object_config,full_config)
        vrf_id = self.match_one(NatPool.NAT_POOL_GENERIC_REGEX,group=1)
        self.netmask = self.match_one(NatPool.NAT_POOL_GENERIC_REGEX,group=4)
        self.start_ip = ip_address.IpAddress(self.match_one(NatPool.NAT_POOL_GENERIC_REGEX,group=2),self.netmask)
        self.end_ip = ip_address.IpAddress(self.match_one(NatPool.NAT_POOL_GENERIC_REGEX,group=3),self.netmask)
        self.overloads = self._build_overloads(vrf_id)

    def _build_overloads(self, vrf_id):
        pool_overloads = []

        regex = NatPoolOverload.NAT_POOL_OVERLOAD_VRF_REGEX % (vrf_id,vrf_id)

        for object_config in self.full_config.find_objects(regex):
            pool_overloads.append(NatPoolOverload(object_config, self.full_config, vrf_id))

        return pool_overloads

    def __repr__(self):
        return "<{} {} {} {} {}>".format(self.__class__.__name__, self.start_ip, self.end_ip, self.netmask, self.overloads)

class AccessList(BaseObject):
    ACCESS_LIST_GENERIC_REGEX = "ip access-list standard neutron_acl_(\d+)_(\w{1,8})"
    ACCESS_LIST_VRF_REGEX = "ip access-list standard neutron_acl_%s_(\w{1,8})"

    ACCESS_LIST_CHILD_REGEX = ("\s*permit (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")

    def __init__(self, object_config, full_config):
        super(AccessList, self).__init__(object_config,full_config)
        self.id = self.match_one(AccessList.ACCESS_LIST_GENERIC_REGEX,group=2)
        self.encapsulation = self.match_one(AccessList.ACCESS_LIST_GENERIC_REGEX,group=1)
        self.permit = []


        stansas = self.object_config.re_search_children(AccessList.ACCESS_LIST_CHILD_REGEX)
        for stansa in stansas:
            self.permit.append(ip_address.IpAddress(self.match(AccessList.ACCESS_LIST_CHILD_REGEX,stansa.text,group=1),self.match(AccessList.ACCESS_LIST_CHILD_REGEX,stansa.text,group=2)))




    def __repr__(self):
        return "<{} {} {} {}>".format(self.__class__.__name__, self.id, self.encapsulation,self.permit)

class Route(BaseObject):
    DEFAULT_ROUTE_ROUTE_GENERIC_REGEX = ("ip route vrf " +
     TenantVrf.NROUTER_REGEX + " 0\.0\.0\.0 0\.0\.0\.0 \S+\.(\d+)"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")

    TENANT_ROUTE_ROUTE_GENERIC_REGEX = ("ip route vrf " +
     TenantVrf.NROUTER_REGEX + " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")

    DEFAULT_ROUTE_ROUTE_VRF_REGEX = ("ip route vrf " +
     N_ROUTER_PREFIX + "%s 0\.0\.0\.0 0\.0\.0\.0 \S+\.(\d+)"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")

    TENANT_ROUTE_ROUTE_VRF_REGEX = ("ip route vrf " +
     N_ROUTER_PREFIX + "%s (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    " (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")

    def __init__(self, object_config, full_config, default=False):
        super(Route, self).__init__(object_config,full_config)

        self.default=default
        self.destination = None
        self.encapsulation = None
        self.next_hop = None
        if default:
            self.__init_default()
        else:
            self.__init()


    def __init_default(self):
        self.destination = ip_address.IpAddress("0.0.0.0","0.0.0.0")
        self.encapsulation = self.match_one(Route.DEFAULT_ROUTE_ROUTE_GENERIC_REGEX,group=2)
        self.next_hop = ip_address.IpAddress(self.match_one(Route.DEFAULT_ROUTE_ROUTE_GENERIC_REGEX,group=3))


    def __init(self):
        self.destination = ip_address.IpAddress(self.match_one(Route.TENANT_ROUTE_ROUTE_GENERIC_REGEX,group=2),self.match(Route.TENANT_ROUTE_ROUTE_GENERIC_REGEX,group=3))
        self.next_hop = ip_address.IpAddress(self.match_one(Route.TENANT_ROUTE_ROUTE_GENERIC_REGEX,group=4))

    def __repr__(self):
        return "<{} {} {} {}>".format(self.__class__.__name__, self.destination, self.encapsulation,self.next_hop)



class GlobalInterface(BaseInterface):

    @staticmethod
    def from_device_config(config):
        interfaces = []
        for object_config in config.find_objects(BaseInterface.INTF_REGEX):
            interface = GlobalInterface(object_config,config)

            if interface.match_one(BaseInterface.INTF_EXT_DESC_REGEX):

                interfaces.append(interface)

        return interfaces

    def __init__(self,object_config,full_config):
        super(GlobalInterface, self).__init__(object_config,full_config)

class DeviceConfig(object):

    def __init__(self, driver, mock=False):
        self.driver = driver
        self.config = None
        self.mock = mock

    def get_device_config(self):
        if self.config is not None:
            return self.config

        if self.mock:
            raw_config = test_config.DEVICE_CONFIG
        else:
            raw_config = self._get_device_config()



        if raw_config:



            root = ET.fromstring(raw_config)
            running_config = root[0][0]
            rgx = re.compile("\r*\n+")
            ioscfg = rgx.split(running_config.text)

            self.config = HTParser(ioscfg)


            return  self.config

    def _get_device_config(self):
        return self.driver._get_connection().get_config(source="running")



    def get_vrfs(self):
        #return TenantVrf.from_device_config(self.get_device_config())
        return asr1k_device_config_parser.Asr1kVrfParser.from_device_config(self.get_device_config())

    def get_global_interfaces(self):
        return GlobalInterface.from_device_config(self.get_device_config())


class NeutronConfig(object):

    def __init__(self, service_helper, mock=False):
        self.service_helper = service_helper
        self.config  = None
        self.mock = mock


    def get_neutron_config(self):
        if self.config is not None:
            return self.config

        if self.mock:
            self.config = test_config.NEUTRON_CONFIG
        else:
            self.config = self.service_helper._fetch_router_info(all_routers=True)

        return self.config


