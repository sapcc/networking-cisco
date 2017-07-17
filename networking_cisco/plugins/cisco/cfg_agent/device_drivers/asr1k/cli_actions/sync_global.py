
import base_action
from networking_cisco.plugins.cisco.cfg_agent.service_helpers import routing_svc_helper
from networking_cisco.plugins.cisco.common import (cisco_constants as c_constants)
import pprint as pp
from oslo_log import log as logging


LOG = logging.getLogger(__name__)


class SyncGlobal(base_action.BaseAction):

    def __init__(self, namespace):
        super(SyncGlobal, self).__init__(namespace)

    def execute(self):
        if not self.confirm:
            print("This is a high risk action. To proceed add --confirm flag")
            exit(0)


        routers = self.routing_service_helper._fetch_router_info(router_ids=[self.router_id])

        if len(routers)==1:
            router = routers[0]

            print pp.pformat(router)

            if router[routing_svc_helper.ROUTER_ROLE_ATTR] != c_constants.ROUTER_ROLE_GLOBAL:
                print("Specified router is not a global Router")
                exit(0)

            driver = self.routing_service_helper.driver_manager.set_driver(router)
            ri = routing_svc_helper.RouterInfo(self.router_id, router)


            for gw_port in router.get('_interfaces',[]):
                if self.port_id is None or gw_port['id']==self.port_id:
                    port_subnets = sorted(gw_port['subnets'], key=routing_svc_helper.itemgetter('id'))

                    self.routing_service_helper._set_subnet_info(gw_port, port_subnets[0]['id'])

                    self.routing_service_helper._external_gateway_added(ri, gw_port)

                    # Process the secondary subnets. Only router ports of global
                    # routers can have multiple ipv4 subnets since we connect such
                    # routers to external networks using regular router ports.
                    for gw_port_sn in port_subnets[1:]:
                         self.routing_service_helper._set_subnet_info(gw_port, gw_port_sn['id'], is_primary=False)
                         self.routing_service_helper._external_gateway_added(ri, gw_port)


                    itfc_name = driver._get_interface_name_from_hosting_port(gw_port)
                    driver._add_interface_nat(itfc_name, 'outside')

            print("Global Router {} synced with hosting device".format(self.router_id))

        else:
            print("Global Router {} not found".format(self.router_id))


