
import base_action

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class Sync(base_action.BaseAction):

    def __init__(self, namespace):
        super(Sync, self).__init__(namespace)

    def execute(self):
        routers = self.routing_service_helper._fetch_router_info(router_ids=[self.router_id])

        if len(routers)==1:
            router = routers[0]
            self.routing_service_helper.driver_manager.set_driver(router)
            self.routing_service_helper.updated_routers.add(self.router_id)
            self.routing_service_helper.process_service()
            print("Router {} synchronized with hosting device".format(self.router_id))
        else:
            print("Router {} not found".format(self.router_id))

