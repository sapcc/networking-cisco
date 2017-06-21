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

from neutron.plugins.ml2.drivers.mech_agent import SimpleAgentMechanismDriverBase
import constants

from bisect import bisect
from neutron.extensions import portbindings
from neutron._i18n import _LE, _LI, _LW
from networking_cisco import backwards_compatibility as bc
from neutron.plugins.common import constants as p_const
import logging

LOG = logging.getLogger(__name__)


class CiscoUcsmBareMetalDriver(SimpleAgentMechanismDriverBase):
    def __init__(self):
        vif_details = {portbindings.CAP_PORT_FILTER: False,
                       portbindings.OVS_HYBRID_PLUG: False}

        super(CiscoUcsmBareMetalDriver, self).__init__(constants.AGENT_TYPE,
                                                       portbindings.VIF_TYPE_OTHER,
                                                       vif_details,
                                                       supported_vnic_types=[portbindings.VNIC_BAREMETAL]
                                                       )

    def bind_port(self, context):
        LOG.debug("Attempting to bind port %(port)s on "
                  "network %(network)s",
                  {'port': context.current['id'],
                   'network': context.network.current['id']})
        vnic_type = context.current.get(portbindings.VNIC_TYPE,
                                        portbindings.VNIC_NORMAL)
        if vnic_type not in self.supported_vnic_types:
            LOG.debug("Refusing to bind due to unsupported vnic_type: %s",
                      vnic_type)
            return

        agents = context._plugin.get_agents(context._plugin_context,
                                       filters={'agent_type': [self.agent_type]})
        if not agents:
            LOG.warning(_LW("Port %(pid)s on network %(network)s not bound, "
                            "no agent registered of tpy %(host)s"),
                        {'pid': context.current['id'],
                         'network': context.network.current['id'],
                         'agent_type': self.agent_type})
        for agent in agents:
            LOG.debug("Checking agent: %s", agent)
            if agent['alive']:
                for segment in context.segments_to_bind:
                    if self.try_to_bind_segment_for_agent(context, segment,
                                                          agent):
                        LOG.debug("Bound using segment: %s", segment)
                        return
            else:
                LOG.warning(_LW("Refusing to bind port %(pid)s to dead agent: "
                                "%(agent)s"),
                            {'pid': context.current['id'], 'agent': agent})

    def try_to_bind_segment_for_agent(self, context, segment, agent):
        mac_address = context.current['mac_address'].lower()
        mac_blocks = agent['configurations'].get('mac_blocks', [])

        # bisect will yield the pos (i) behind the last value, which is <=.
        # i-1 would then be the block containing the mac address
        # 'z' is always larger than a mac address, so if the mac_address
        # coincides with the beginning of a block, it will still yield a position
        # after the block, as it will if the mac_address is behind the beginning of the block
        pos = bisect.bisect(mac_blocks, (mac_address, 'z')) - 1

        if pos < 0:
            LOG.debug("Mac address out of range for agent")
            return False

        if mac_address < mac_blocks[pos][0] or mac_blocks[pos][1] < mac_address:
            LOG.debug("Mac address out of range for agent")
            return False

        return SimpleAgentMechanismDriverBase.try_to_bind_segment_for_agent(self, context, segment, agent)

    def get_allowed_network_types(self, _=None):
        return p_const.TYPE_FLAT, p_const.TYPE_VLAN

    def get_mappings(self, agent):
        items = []
        for item in agent['configurations'].get('physical_networks', []):
            if isinstance(item, list):
                items.extend(item)
            else:
                items.append(item)

        return items
