# Copyright 2017 SAP SE
# All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import os

if not os.environ.get('DISABLE_EVENTLET_PATCHING'):
    import eventlet

    eventlet.monkey_patch()

import six
import sys
import logging
import attr

from contextlib import contextmanager
from collections import defaultdict

from oslo_utils import importutils
from oslo_config import cfg
from oslo_service import service
import oslo_messaging

from neutron._i18n import _LE, _LI, _LW
from neutron.common import config as common_config
try:
    from neutron.common import profiler
except ImportError:
    profiler = None
from neutron.common import topics
from neutron.plugins.ml2.drivers.agent import _agent_manager_base as amb
from neutron.plugins.ml2.drivers.agent import _common_agent as ca
from networking_cisco.plugins.ml2.drivers.cisco.ucsm import exceptions as cexc

import constants
from config import UcsmBmConfig

import ssl

###
# Basing it of CommonAgentManagerBase imposes some requirements,
# which may make the code look uncessecary complicated:
# - The manager needs to return a device in the known devices,
#   before ever receiving a port_binding request, other it will be filtered out,
#   as the base assumes, that it is not intended for this manager
#   => We know only MACs, so we return them
#      (CiscoUcsmBareMetalManager#get_all_devices)
# For getting the VLAN, we need to specify the device and the binding host.
# - The binding host is the uuid of the ironic bare-metal node, which we do not
#   know. But prior the binding, we receive a port_update, which allows us to
#   remember that association.
#   It does also gives us the UUID of the port, which we need to remember.
#   We do not receive the segment for our agent here though.
# - Ironic creates two ports with the same MAC, one in the management network,
#   the other one in the tenant network. Querying the device for the MAC
#   might give you either, so we have to query the port for its UUID
#   (which we have stored in CiscoUcsmBareMetalRpc#port_update)
# - Finally, as we query the device via the port UUID, the attribute 'device'
#   will be the UUID, the base expects it to be the MAC, as we return them in
#   CiscoUcsmBareMetalManager#get_all_devices.
#   => We have to change the 'device' field back to a MAC in
#      (AgentLoop#_get_devices_details_list)

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

LOG = logging.getLogger(__name__)

def create_dn_wcard_filter(ucsmsdk, filter_class, filter_value):
    """ Creates wild card filter object for given class name, and values.
        :param filter_class: class name
	    :param filter_value: filter property value
	    :return WcardFilter: WcardFilter object
        """
    wcard_filter = ucsmsdk.WcardFilter()
    wcard_filter.Class = filter_class
    wcard_filter.Property = "dn"
    wcard_filter.Value = filter_value
    return wcard_filter

def create_dn_in_filter(ucsmsdk, filter_class, filter_value):
    """ Creates filter object for given class name, and DN values."""
    in_filter = ucsmsdk.FilterFilter()
    in_filter.AddChild(create_dn_wcard_filter(ucsmsdk, filter_class, filter_value))
    return in_filter


def get_resolve_class(handle, class_id,
                      in_filter, in_heir=False):
    return handle.ConfigResolveClass(
        class_id, in_filter,
        inHierarchical=in_heir)

class CiscoUcsmBareMetalRpc(amb.CommonAgentManagerRpcCallBackBase):
    target = oslo_messaging.Target(version='1.4')

    def security_groups_rule_updated(self, context, **kwargs):
        pass

    def security_groups_member_updated(self, context, **kwargs):
        pass

    def security_groups_provider_updated(self, context, **kwargs):
        pass

    def network_delete(self, context, **kwargs):
        pass

    def port_update(self, context, **kwargs):
        port = kwargs['port']
        LOG.debug("port_update received for port %s ", port)
        self.agent.mgr.set_mapping(port)
        self.updated_devices.add(port['mac_address'])

@attr.s
class _PortInfo(object):
    port_id = attr.ib(default=None)
    ucsm_ip = attr.ib(default=None)
    binding_host_id = attr.ib(default=None)

class CiscoUcsmBareMetalManager(amb.CommonAgentManagerBase):
    def __init__(self, config):
        super(amb.CommonAgentManagerBase, self).__init__()
        self.ucsm_conf = config
        self._ports = defaultdict(_PortInfo)
        self.ucsmsdk = None

        self._discover_devices()

    def get_rpc_callbacks(self, context, agent, sg_agent):
        return CiscoUcsmBareMetalRpc(context, agent, sg_agent)

    def ensure_port_admin_state(self, device, admin_state_up):
        pass

    def set_mapping(self, port):
        port_id = port['id']
        mac = port['mac_address']
        binding_host_id = port['binding:host_id']

        LOG.debug("Bound {} to {}".format(mac, binding_host_id))
        info = self._ports[mac.lower()]
        info.port_id = port_id
        info.binding_host_id = binding_host_id

    def get_agent_configurations(self):
        # The very least, we have to return the physical networks as keys
        # of the bridge_mappings
        return {'physical_networks': self.ucsm_conf.get_networks(),
                'all_devices': six.viewkeys(self._ports) }

    def get_agent_id(self):
        return 'cisco-ucs-bm-agent-%s' % cfg.CONF.host

    def get_all_devices(self):
        return set(six.iterkeys(self._ports))

    def get_devices_modified_timestamps(self, devices):
        return {}

    def get_extension_driver_type(self):
        return 'ucsm_bm'

    def get_port_info(self, device):
        if device in self._ports:
            return self._ports[device.lower()]

    def get_rpc_consumers(self):
        consumers = [[topics.PORT, topics.UPDATE],
                     [topics.NETWORK, topics.DELETE]]
        return consumers

    def plug_interface(self, network_id, network_segment, device, device_owner):
        LOG.debug("Start {}".format(device))
        eth_if_class_id = self.ucsmsdk.VnicEtherIf.ClassId()
        eth_class_id = self.ucsmsdk.VnicEther.ClassId()
        vlan_id = network_segment.segmentation_id
        info = self._ports.get(device.lower())
        if not info or not info.ucsm_ip:
            LOG.debug("Unknown device {}".format(device))
            return False

        with self.ucsm_connect_disconnect(info.ucsm_ip) as handle:
            vlans = self._get_vlan(handle, vlan_id)
            if len(vlans) != 1:
                LOG.error("Cannot uniquely identify vlan {} for {}".format(vlan_id, device))
                return False
            vlan = vlans[0]

            handle.StartTransaction()
            for eth in handle.GetManagedObject(None, eth_class_id, {self.ucsmsdk.VnicEther.ADDR: device} ):
                found = False
                crc = get_resolve_class(handle, eth_if_class_id, create_dn_in_filter(self.ucsmsdk, eth_if_class_id, eth.Dn))

                if crc.errorCode != 0:
                    LOG.error("Could not get ether_ifs for {}".format(eth.Dn))
                    handle.UndoTransaction()
                    return False

                exists = False
                to_delete = []
                for eth_if in crc.OutConfigs.GetChild():
                    if eth_if.Name != vlan.Name:
                        to_delete.append(eth_if)
                    else:
                        exists = True

                if to_delete:
                    LOG.debug("Removing {}".format([eth_if.Dn for eth_if in to_delete]))
                    handle.RemoveManagedObject(inMo=to_delete)

                if exists:
                    LOG.debug("Already bound {}".format(vlan.Name))
                else:
                    vlan_path = (eth.Dn + constants.VLAN_PATH_PREFIX + vlan.Name)

                    LOG.debug("Adding {}".format(vlan.Name))

                    handle.AddManagedObject(eth,
                        self.ucsmsdk.VnicEtherIf.ClassId(),
                        {self.ucsmsdk.VnicEtherIf.DN: vlan_path,
                        self.ucsmsdk.VnicEtherIf.NAME: vlan.Name,
                        self.ucsmsdk.VnicEtherIf.DEFAULT_NET: "yes"}, True)
            handle.CompleteTransaction()

        LOG.debug("Done")
        return True

    def _get_vlan(self, handle, vlan_id):
        return handle.GetManagedObject(None, self.ucsmsdk.FabricVlan.ClassId(), {
            self.ucsmsdk.FabricVlan.ID: vlan_id,
            self.ucsmsdk.FabricVlan.TRANSPORT: 'ether',
            self.ucsmsdk.FabricVlan.IF_TYPE: 'virtual',
            self.ucsmsdk.FabricVlan.TYPE: 'lan'} )

    def setup_arp_spoofing_protection(self, device, device_details):
        pass

    def delete_arp_spoofing_protection(self, devices):
        pass

    def delete_unreferenced_arp_protection(self, current_devices):
        pass

    @contextmanager
    def ucsm_connect_disconnect(self, ucsm_ip):
        handle = self.ucs_manager_connect(ucsm_ip)
        try:
            yield handle
        finally:
            self.ucs_manager_disconnect(handle, ucsm_ip)

    def ucs_manager_connect(self, ucsm_ip):
        """Connects to a UCS Manager."""
        if not self.ucsmsdk:
            self.ucsmsdk = self._import_ucsmsdk()

        username, password = self.ucsm_conf.get_credentials_for_ucsm_ip(ucsm_ip)
        if not username:
            LOG.error(_LE('UCS Manager network driver failed to get login '
                          'credentials for UCSM %s'), ucsm_ip)
            return None

        handle = self.ucsmsdk.UcsHandle()
        try:
            handle.Login(ucsm_ip, username, password)
        except Exception as e:
            # Raise a Neutron exception. Include a description of
            # the original  exception.
            raise cexc.UcsmConnectFailed(ucsm_ip=ucsm_ip, exc=e)

        return handle

    def ucs_manager_disconnect(self, handle, ucsm_ip):
        """Disconnects from the UCS Manager.

        After the disconnect, the handle associated with this connection
        is no longer valid.
        """
        try:
            handle.Logout()
        except Exception as e:
            # Raise a Neutron exception. Include a description of
            # the original  exception.
            raise cexc.UcsmDisconnectFailed(ucsm_ip=ucsm_ip, exc=e)

    def _import_ucsmsdk(self):
        """Imports the Ucsm SDK module.

        This module is not installed as part of the normal Neutron
        distributions. It is imported dynamically in this module so that
        the import can be mocked, allowing unit testing without requiring
        the installation of UcsSdk.

        """
        return importutils.import_module('UcsSdk')

    def _discover_devices(self):
        for ucsm_ip in self.ucsm_conf.get_all_ucsm_ips():
            vnic_paths = self.ucsm_conf.vnic_paths_dict[ucsm_ip]
            with self.ucsm_connect_disconnect(ucsm_ip) as handle:
                for vnic_path in vnic_paths:
                    for mac in self._get_devices(handle, vnic_path):
                        self._ports[mac.lower()].ucsm_ip = ucsm_ip

    def _get_devices(self, handle, vnic_path):
        vnic_id = self.ucsmsdk.VnicEther.ClassId()
        crc = get_resolve_class(handle, vnic_id, create_dn_in_filter(self.ucsmsdk, vnic_id, vnic_path))
        if crc.errorCode != 0:
            LOG.debug("Could not resolve vnics with path {}".format(vnic_path))
        else:
            for child in crc.OutConfigs.GetChild():
                if child.Addr != 'derived':
                    yield child.Addr

class AgentLoop(ca.CommonAgentLoop):
    def _get_devices_details_list(self, devices):
        devices_by_host = defaultdict(list)
        for device in devices:
            port_info = self.mgr.get_port_info(device)
            if port_info and port_info.binding_host_id and port_info.port_id:
                devices_by_host[port_info.binding_host_id].append(port_info.port_id)
        device_details = []
        for host, devices_on_host in six.iteritems(devices_by_host):
            LOG.debug("Querying {} for {}".format(devices_on_host, host))
            for device in self.plugin_rpc.get_devices_details_list(self.context, devices_on_host, self.agent_id, host=host):
                device['device'] = device['mac_address']
                device_details.append(device)

        LOG.debug("Found {}".format(device_details))
        return device_details

def main():
    common_config.init(sys.argv[1:])
    common_config.setup_logging()
    if profiler:
        profiler.setup(constants.AGENT_BINARY, cfg.CONF.host)
    config = UcsmBmConfig()
    manager = CiscoUcsmBareMetalManager(config)

    polling_interval = cfg.CONF.AGENT.polling_interval
    quitting_rpc_timeout = cfg.CONF.AGENT.quitting_rpc_timeout
    agent = AgentLoop(manager, polling_interval,
                      quitting_rpc_timeout,
                      constants.AGENT_TYPE,
                      constants.AGENT_BINARY)
    LOG.info(_LI("Agent initialized successfully, now running... "))
    launcher = service.launch(cfg.CONF, agent)
    launcher.wait()
