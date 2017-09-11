import re

from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k.models import ip_address
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k.models import vrf as vrf_model
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k.models import interfaces as interfaces_model


N_ROUTER_PREFIX = "nrouter-"#routertype.N_ROUTER_PREFIX

class Asr1kConfigParser(object):

    def __init__(self,object_config,device_config):
        self.device_config = device_config
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


class Asr1kInterfaceParser(Asr1kConfigParser):

    INTF_REGEX = "interface (\S+)\.(\d+)"
    INTF_DESC_REGEX = "\s*description (OPENSTACK_NEUTRON_INTF|OPENSTACK_NEUTRON_EXTERNAL_INTF)"
    INTF_EXT_DESC_REGEX = "\s*description (OPENSTACK_NEUTRON_EXTERNAL_INTF)"
    INTF_V4_ADDR_REGEX = "\s*ip address (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$"
    INTF_V4_SECONDARY_ADDR_REGEX = "\s*ip address (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) secondary$"
    HSRP_V4_VIP_REGEX = "\s*standby (\d+) ip (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$"
    HSRP_V4_SECONDARY_VIP_REGEX = "\s*standby (\d+) ip (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) secondary$"
    HSRP_PRIORITY_REGEX = "\s*standby (\d+) priority (\d+)"
    HSRP_GROUP_REGEX = "\s*standby (\d+) name neutron-hsrp-(\d+)-(\d+)"
    INTF_NAT_REGEX = "\s*ip nat (inside|outside)"


    @staticmethod
    def from_device_config(device_config,vrf_id=None):
        if vrf_id is not None :
            return Asr1kInterfaceParser.build_internal(device_config,vrf_id)
        else:
            return Asr1kInterfaceParser.build_gateway(device_config)

    @staticmethod
    def build_internal(device_config,vrf_id):
        vrf_name = N_ROUTER_PREFIX+vrf_id

        runcfg_intfs = [obj for obj in device_config.find_objects(Asr1kInterfaceParser.INTF_REGEX)
                        if obj.re_search_children(vrf_name)]
        interfaces = []

        for interface_conf in runcfg_intfs:
            interface_parser = Asr1kInterfaceParser(interface_conf, device_config)
            interfaces.append(interface_parser.from_config(internal=True))

        return interfaces

    @staticmethod
    def build_gateway(device_config):
        pass


    def __init__(self,interface_conf,device_config):
        super(Asr1kInterfaceParser, self).__init__(interface_conf,device_config)


    def from_config(self,internal=True):

        if(internal):
            interface = interfaces_model.InternalInterface()
        else:
            interface = interfaces_model.GatewayInterface()

        interface.parent_interface = self.match(Asr1kInterfaceParser.INTF_REGEX)
        interface.encapsulation = self.match(Asr1kInterfaceParser.INTF_REGEX,group=2)
        interface.description = self.match_one(Asr1kInterfaceParser.INTF_DESC_REGEX)

        interface.nat_mode = self.match_one(Asr1kInterfaceParser.INTF_NAT_REGEX)
        interface.primary_ip = self.__parse_primary_ip(Asr1kInterfaceParser.INTF_V4_ADDR_REGEX)
        interface.secondary_ips= self.__parse_secondary_ips(Asr1kInterfaceParser.INTF_V4_SECONDARY_ADDR_REGEX)

        #interface.ha_info= interfaces_model.HaInfo(self.object_config,self.full_config)

        return interface


    def __parse_primary_ip(self,regex):
        return ip_address.IpAddress(self.match_one(regex),self.match_one(regex,2))

    def __parse_secondary_ips(self,regex):
        result =[]
        stansas = self.object_config.re_search_children(regex)
        for stansa in stansas:
            result.append(ip_address.IpAddress(self.match(regex,stansa.text,1),self.match(regex,stansa.text,2)))
        return result


class Asr1kVrfParser(Asr1kConfigParser):

    NROUTER_REGEX = N_ROUTER_PREFIX + "(\w{6,6})"
    VRF_REGEX = "vrf definition " + NROUTER_REGEX

    @staticmethod
    def from_device_config(device_config):
        vrfs = []
        for vrf_config in device_config.find_objects(Asr1kVrfParser.VRF_REGEX):
            parser = Asr1kVrfParser(vrf_config,device_config)
            vrfs.append(parser.from_config())
        return vrfs

    def __init__(self,vrf_config,device_config):
        super(Asr1kVrfParser, self).__init__(vrf_config,device_config)

    def from_config(self):

        vrf = vrf_model.Vrf()

        vrf.id = self.match(Asr1kVrfParser.VRF_REGEX)
        vrf.interfaces = self.__build_interfaces(vrf.id)
        # self.global_interface = None #TODO based on HRSP
        # self.static_nats = self.__build_static_nat()
        # self.nat_overloads = self.__build_nat_overload()
        # self.nat_pools = self.__build_nat_pools()
        #
        # self.default_route = self.__build_default_route()
        # self.routes = self.__build_routes()
        # self.access_lists = self.__build_access_lists()
        return vrf



    def __build_interfaces(self,vrf_id=None):

        return  Asr1kInterfaceParser.from_device_config(self.device_config,vrf_id,)



