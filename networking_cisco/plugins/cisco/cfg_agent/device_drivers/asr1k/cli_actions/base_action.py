from oslo_config import cfg
from oslo_utils import importutils
from oslo_log import log as logging
from neutron.common import config as common_config

from networking_cisco import backwards_compatibility as bc
from networking_cisco.plugins.cisco.cfg_agent import cfg_agent
from networking_cisco.plugins.cisco.device_manager import config


LOG = logging.getLogger(__name__)


class BaseAction(object):
    def register_opts(self, conf):
        conf.register_opts(bc.core_opts)
        conf.register_opts(cfg_agent.OPTS, "cfg_agent")
        bc.config.register_agent_state_opts_helper(conf)
        bc.config.register_root_helper(conf)

    def __init__(self,namespace):
        print(namespace)
        self.router_id = namespace.router_id
        self.port_id = namespace.port_id
        self.config_files = namespace.config
        self.confirm = namespace.confirm
        self.conf = cfg.ConfigOpts()
        self.register_opts(self.conf)
        args = ['--config-file=' + file for file in self.config_files]
        self.conf(project='neutron', args=args)
        common_config.init(args)
        bc.config.setup_logging()

        self._initialize_service_helpers(self.conf.host)
        self._credentials = (
            config.obtain_hosting_device_credentials_from_config())

    def get_hosting_device_password(self, credentials_id):
        creds = self._credentials.get(credentials_id)
        return creds['password'] if creds else None


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