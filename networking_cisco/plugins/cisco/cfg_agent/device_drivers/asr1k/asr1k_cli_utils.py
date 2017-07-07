import argparse
from oslo_utils import importutils

ACTION_MODULE = 'networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k.cli_actions.'

class Execute(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super(Execute, self).__init__(option_strings, dest, **kwargs)
        self.actions = {"validate":"validate.Validate","sync":"sync.Sync","delete":"delete.Delete"}

    def __call__(self, parser, namespace, values, option_string=None):
        action = self.actions.get(values)
        if action:

            instance = importutils.import_object(ACTION_MODULE+action,namespace)


            instance.execute()


def main():
    parser = argparse.ArgumentParser(prog='asr1k_utils', description='Operations utilities for ASR1k driver.')

    parser.add_argument('router_id',
                       help='router id',action='store')
    parser.add_argument('command',
                       help='command to execute',action=Execute,choices=["validate", "sync","delete"])

    parser.add_argument('--config-file', dest='config', action='append',
                       default=["/etc/neutron/plugins/cisco/cisco_cfg_agent.ini", "/etc/neutron/neutron.conf"],
                       help='Configuration files')

    parser.parse_args()
