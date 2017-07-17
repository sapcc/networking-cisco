
import base_action
from networking_cisco.plugins.cisco.cfg_agent.service_helpers import routing_svc_helper
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
            router['enable_snat']=False
            driver = self.routing_service_helper.driver_manager.set_driver(router)

            print pp.pformat(router)

            ri = routing_svc_helper.RouterInfo(self.router_id, router)



            for gw_port in router.get('_interfaces',[]):
                if self.port_id is None or gw_port['id']==self.port_id:
                    self.routing_service_helper._set_subnet_info(gw_port, gw_port['subnets'][0]['id'])

                    self.routing_service_helper._internal_network_added(ri, gw_port, gw_port)

                    # Process the secondary subnets. Only router ports of global
                    # routers can have multiple ipv4 subnets since we connect such
                    # routers to external networks using regular router ports.
                    for gw_port_sn in gw_port['subnets'][1:]:
                         self.routing_service_helper._set_subnet_info(gw_port, gw_port_sn['id'], is_primary=False)
                         self.routing_service_helper._internal_network_added(ri, gw_port, gw_port)




            print("Global Router {} synced with hosting device".format(self.router_id))

        else:
            print("Global Router {} not found".format(self.router_id))


