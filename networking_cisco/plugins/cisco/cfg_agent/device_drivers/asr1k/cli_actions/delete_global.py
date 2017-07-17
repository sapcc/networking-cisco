
import base_action
from networking_cisco.plugins.cisco.cfg_agent.service_helpers import routing_svc_helper


from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class DeleteGlobal(base_action.BaseAction):

    def __init__(self, namespace):
        super(DeleteGlobal, self).__init__(namespace)

    def execute(self):
        if not self.confirm:
            print("This is a high risk action. To proceed add --confirm flag")
            exit(0)


        routers = self.routing_service_helper._fetch_router_info(router_ids=[self.router_id])

        if len(routers)==1:
            router = routers[0]
            driver = self.routing_service_helper.driver_manager.set_driver(router)

            for gw_port in router.get('_interfaces',[]):

                if self.port_id is None or gw_port['id']==self.port_id:

                    driver.external_gateway_removed(routing_svc_helper.RouterInfo(self.router_id, router), gw_port)


            print("Global Router {} deleted from hosting device".format(self.router_id))

        else:
            print("Global Router {} not found".format(self.router_id))


