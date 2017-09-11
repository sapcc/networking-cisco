
import base_action
from oslo_log import log as logging
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k import asr1k_cfg_syncer
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k.validator import running_config as rc
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k.validator import models

LOG = logging.getLogger(__name__)

class Validate(base_action.BaseAction):

    def __init__(self, namespace):
        super(Validate, self).__init__(namespace)


    def execute(self):
        print("Validate")

        neutron_config = models.NeutronConfig(self.routing_service_helper, mock=False)

        print(neutron_config.get_neutron_config())

        # routers = self.routing_service_helper._fetch_router_info(router_ids=[self.router_id])
        #
        # if len(routers)==1:
        #     router = routers[0]
        #     # hosting_device = router.get('routerhost:hosting_device')
        #
        #     driver = self.routing_service_helper.driver_manager.set_driver(router)            #
        #
        #     running_config = rc.RunningConfig(driver)
        #
        #     vrfs = running_config.get_vrfs()
        #
        #     print(vrfs)
        #
        # else:
        #     print("Router {} not found".format(self.router_id))
        #
        #
        #
