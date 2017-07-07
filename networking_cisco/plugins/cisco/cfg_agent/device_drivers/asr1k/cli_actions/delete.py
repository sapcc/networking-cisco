
import base_action
from networking_cisco.plugins.cisco.cfg_agent.service_helpers import routing_svc_helper

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class Delete(base_action.BaseAction):

    def __init__(self, namespace):
        super(Delete, self).__init__(namespace)

    def execute(self):

        routers = self.routing_service_helper._fetch_router_info(router_ids=[self.router_id])

        if len(routers)==1:
            router = routers[0]
            self.routing_service_helper.driver_manager.set_driver(router)
            self.routing_service_helper.router_info = {self.router_id: routing_svc_helper.RouterInfo(self.router_id, router)}
            self.routing_service_helper.removed_routers.add(self.router_id)
            self.routing_service_helper.process_service()
            print("Router {} delete from hosting device".format(self.router_id))

        else:
            print("Router {} not found".format(self.router_id))


