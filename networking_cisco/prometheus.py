import os
from oslo_log import log as logging

from prometheus_client import start_http_server
from prometheus_client import Counter
from prometheus_client import Gauge


LOG = logging.getLogger(__name__)


def metric(metric=None,action=None,**action_args):

    p = Prometheus()

    def decorator(func):
        def func_wrapper(*args, **kwargs):

            ret_val = func(*args, **kwargs)

            hosting_device = args[0].hosting_device

            labels = []

            if hosting_device:
                labels.append(hosting_device['id'])
            else:
                labels.append(None)

            m = getattr(p, metric)
            if m:


                if labels:
                    a = getattr(m.labels(labels), action)
                else:
                    a = getattr(m,action)

                if a:
                    a(**action_args)

            return ret_val

        return func_wrapper
    return decorator


class Prometheus:

    class __Prometheus:

        def __init__(self):
            self.floating_ip = Gauge('asr_floating_ips', 'Number of managed Floating IPs', ['hosting_device'])
            self.interface = Gauge('asr_interfaces', 'Number of managed Interfaces', ['hosting_device'])
            self.ext_gateway = Gauge('asr_ex_gw_ports', 'Number of managed Gateway Ports', ['hosting_device'])
            self.router = Gauge('asr_routers', 'Number of managed Routers', ['hosting_device'])
            self.hosting_device = Counter('asr_hosting_devices', 'Number of managed Hosting devices')

            self.sync_delete_nat_pool = Counter('asr_sync_delete_nat_pool', 'Number of attempts to delete a NAT pool on sync', ['hosting_device'])
            self.sync_delete_nat_pool_overload = Counter('asr_sync_delete_nat_pool_overload', 'Number of attempts to delete an NAT pool overloade on sync', ['hosting_device'])
            self.sync_delete_vrf = Counter('asr_sync_delete_vrf', 'Number of attempts to delete a VRF on sync', ['hosting_device'])
            self.sync_delete_route = Counter('asr_sync_delete_route', 'Number of attempts to delete a route on sync', ['hosting_device'])
            self.sync_delete_snat = Counter('asr_sync_delete_snat', 'Number of attempts to delete an SNAT entry on sync', ['hosting_device'])
            self.sync_delete_acl = Counter('asr_sync_delete_acl', 'Number of attempts to delete an ACL entry on sync', ['hosting_device'])
            self.sync_delete_interface = Counter('asr_sync_delete_interface', 'Number of attempts to delete an interface entry on sync', ['hosting_device'])

            self.router_info_incomplete = Gauge('asr_router_info_incomplete', 'Number of routers with INFO)INCOMPLETE state', ['hosting_device'])



        def start_prometheus_exporter(self):
            port= int(os.environ.get('METRICS_PORT',9102))
            LOG.info("Starting prometheus exporter port port %s",port)
            start_http_server(port)

    instance = None

    def __init__(self):
        if not Prometheus.instance:
            Prometheus.instance = Prometheus.__Prometheus()

    def __getattr__(self, name):
        return getattr(self.instance, name)


