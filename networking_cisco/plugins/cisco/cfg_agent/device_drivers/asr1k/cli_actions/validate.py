
import base_action
from oslo_log import log as logging
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k import asr1k_cfg_syncer


LOG = logging.getLogger(__name__)

class Validate(base_action.BaseAction):

    def __init__(self, namespace):
        super(Validate, self).__init__(namespace)


    def execute(self):

        routers = self.routing_service_helper._fetch_router_info(router_ids=[self.router_id])

        if len(routers)==1:
            # router = routers[0]
            # hosting_device = router.get('routerhost:hosting_device')
            #
            # temp_res = {"id": hosting_device,
            #             "hosting_device": router['hosting_device'],
            #             "router_type": router['router_type']}
            # driver = self.routing_service_helper.driver_manager.set_driver(temp_res)
            #
            #
            # cfg_syncer = asr1k_cfg_syncer.ConfigSyncer([router], driver, router['hosting_device'],test_mode=True)
            # cfg_syncer.delete_invalid_cfg()
            pass
        else:
            print("Router {} not found".format(self.router_id))



