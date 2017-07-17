from oslo_config import cfg
from oslo_utils import importutils
from oslo_log import log as logging
import socket
import sys

from neutron.common import config as common_config

from networking_cisco import backwards_compatibility as bc
from  networking_cisco.plugins.cisco.cfg_agent import cfg_agent


LOG = logging.getLogger(__name__)


class BaseAction(object):


    def __init__(self,namespace):
        print(namespace)
        self.router_id = namespace.router_id
        self.port_id = namespace.port_id
        self.config_files = namespace.config
        self.confirm = namespace.confirm
        self.conf = cfg.CONF
        self.conf.register_opts(cfg_agent.OPTS, "cfg_agent")
        common_config.init("--config-file " + s for s in self.config_files)
        self.host = socket.gethostname()
        self._initialize_service_helpers(self.host)
        bc.config.setup_logging()



    def _initialize_service_helpers(self, host):
        svc_helper_class = self.conf.cfg_agent.routing_svc_helper_class
        try:
            self.routing_service_helper = importutils.import_object(
                svc_helper_class, host, self.conf, self)
        except ImportError as e:
            print("Error in loading routing service helper. Class "
                            "specified is %(class)s. Reason:%(reason)s",
                        {'class': self.conf.cfg_agent.routing_svc_helper_class,
                         'reason': e})
            exit(1)