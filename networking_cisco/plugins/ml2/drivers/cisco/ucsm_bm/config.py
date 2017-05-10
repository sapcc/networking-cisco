# Copyright 2015-2016 Cisco Systems, Inc.
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

import six
from oslo_config import cfg
from oslo_log import log as logging

from networking_cisco._i18n import _

from networking_cisco.plugins.ml2.drivers.cisco.ucsm import constants as const

LOG = logging.getLogger(__name__)

""" Cisco UCS Manager Bare MEtal ML2 Mechanism driver specific configuration.

Following are user configurable options for UCS Manager Bare Metal ML2 Mechanism
driver. A repetitive block starting with ml2_cisco_ucsm_bm_ip signals multi-UCSM
configuration.
"""


class UcsmBmConfig(object):
    """ML2 Cisco Bare Metal UCSM Mechanism Driver Configuration class."""
    ucsm_dict = {}
    ucsm_port_dict = {}
    sp_template_dict = {}
    vnic_template_dict = {}
    physical_network_dict = {}
    vnic_paths_dict = {}
    multi_ucsm_mode = False
    sp_template_mode = False
    vnic_template_mode = False

    def __init__(self):
        """Create a single UCSM or Multi-UCSM dict."""
        self._create_multi_ucsm_dicts()

        if not self.ucsm_dict:
            raise cfg.Error(_('Insufficient UCS Manager configuration has '
                              'been provided to the plugin'))

    def _create_multi_ucsm_dicts(self):
        """Creates a dictionary of all UCS Manager data from config."""
        username = None
        password = None
        multi_parser = cfg.MultiConfigParser()
        read_ok = multi_parser.read(cfg.CONF.config_file)

        if len(read_ok) != len(cfg.CONF.config_file):
            raise cfg.Error(_('Some config files were not parsed properly'))

        for parsed_file in multi_parser.parsed:
            for parsed_item in parsed_file.keys():
                dev_id, sep, dev_ip = parsed_item.partition(':')
                dev_ip = dev_ip.strip()
                if dev_id.lower() == 'ml2_cisco_ucsm_bm_ip':
                    for dev_key, value in parsed_file[parsed_item].items():
                        config_item = dev_key.lower()
                        if config_item == 'sp_template_list':
                            self._parse_sp_template_list(dev_ip, value)
                            self.sp_template_mode = True
                        elif config_item == 'vnic_template_list':
                            self._parse_vnic_template_list(dev_ip, value)
                            self.vnic_template_mode = True
                        elif config_item == 'vnic_paths':
                            self._parse_vnic_paths(dev_ip, value)
                        elif config_item == 'physical_network':
                            self._parse_physical_network(dev_ip, value)
                        elif dev_key.lower() == 'ucsm_username':
                            username = value[0].strip()
                        elif dev_key.lower() == 'ucsm_password':
                            password = value[0].strip()
                        ucsm_info = (username, password)
                        self.ucsm_dict[dev_ip] = ucsm_info

    def get_credentials_for_ucsm_ip(self, ucsm_ip):
        if ucsm_ip in self.ucsm_dict:
            return self.ucsm_dict.get(ucsm_ip)

    def get_all_ucsm_ips(self):
        return self.ucsm_dict.keys()

    def get_ucsm_eth_port_list(self, ucsm_ip):
        if ucsm_ip in self.ucsm_port_dict:
            return self.ucsm_port_dict[ucsm_ip]

    def _parse_sp_template_list(self, ucsm_ip, sp_template_config):
        sp_template_list = []
        for sp_template_temp in sp_template_config:
            sp_template_list = sp_template_temp.split()
            for sp_template in sp_template_list:
                sp_template_path, sep, template_hosts = (
                    sp_template.partition(':'))
                if not sp_template_path or not sep or not template_hosts:
                    raise cfg.Error(_('UCS Mech Driver: Invalid Service '
                                      'Profile Template config %s')
                                    % sp_template_config)
                sp_temp, sep, hosts = template_hosts.partition(':')
                LOG.debug('SP Template Path: %s, SP Template: %s, '
                    'Hosts: %s', sp_template_path, sp_temp, hosts)
                host_list = hosts.split(',')
                for host in host_list:
                    value = (ucsm_ip, sp_template_path, sp_temp)
                    self.sp_template_dict[host] = value
                    LOG.debug('SP Template Dict key: %s, value: %s',
                              host, value)

    def is_service_profile_template_configured(self):
        return self.sp_template_mode

    def get_sp_template_path_for_host(self, host):
        template_info = self.sp_template_dict.get(host)
        # template_info should be a tuple containing
        # (ucsm_ip, sp_template_path, sp_template)
        return template_info[1] if template_info else None

    def get_sp_template_for_host(self, host):
        template_info = self.sp_template_dict.get(host)
        # template_info should be a tuple containing
        # (ucsm_ip, sp_template_path, sp_template)
        return template_info[2] if template_info else None

    def get_ucsm_ip_for_sp_template_host(self, host):
        template_info = self.sp_template_dict.get(host)
        # template_info should be a tuple containing
        # (ucsm_ip, sp_template_path, sp_template)
        return template_info[0] if template_info else None

    def get_sp_template_list_for_ucsm(self, ucsm_ip):
        sp_template_info_list = []
        hosts = self.sp_template_dict.keys()
        for host in hosts:
            value = self.sp_template_dict.get(host)
            if ucsm_ip in value:
                LOG.debug('SP Template: %s in UCSM : %s',
                          value[2], value[0])
                sp_template_info_list.append(value)
        return sp_template_info_list

    def get_networks(self):
        return six.viewvalues(self.physical_network_dict)

    def _parse_physical_network(self, ucsm_ip, physical_network_name):
        self.physical_network_dict[ucsm_ip] = physical_network_name

    def _parse_vnic_paths(self, ucsm_ip, paths):
        self.vnic_paths_dict[ucsm_ip] = paths

    def _parse_vnic_template_list(self, ucsm_ip, vnic_template_config):
        vnic_template_mapping = []
        for vnic_template_temp in vnic_template_config:
            vnic_template_mapping = vnic_template_temp.split()
            for mapping in vnic_template_mapping:
                physnet, sep, vnic_template = mapping.partition(':')
                if not sep or not vnic_template:
                    raise cfg.Error(_("UCS Mech Driver: Invalid VNIC Template "
                                      "config: %s") % physnet)

                vnic_template_path, sep, vnic_template_name = (
                    vnic_template.partition(':'))
                if not vnic_template_path:
                    vnic_template_path = const.VNIC_TEMPLATE_PARENT_DN
                if not vnic_template_name:
                    raise cfg.Error(_("UCS Mech Driver: Invalid VNIC Template "
                                      "name for physnet: %s") % physnet)

                key = (ucsm_ip, physnet)
                value = (vnic_template_path, vnic_template_name)
                self.vnic_template_dict[key] = value
                LOG.debug('VNIC Template key: %s, value: %s',
                    key, value)

    def is_vnic_template_configured(self):
        return self.vnic_template_mode

    def get_vnic_template_for_physnet(self, ucsm_ip, physnet):
        key = (ucsm_ip, physnet)
        if key in self.vnic_template_dict:
            return self.vnic_template_dict.get(key)
        else:
            return (None, None)

    def get_vnic_template_for_ucsm_ip(self, ucsm_ip):
        vnic_template_info_list = []
        keys = self.vnic_template_dict.keys()
        for key in keys:
            LOG.debug('VNIC template dict key : %s', key)
            if ucsm_ip in key:
                value = self.vnic_template_dict.get(key)
                LOG.debug('Appending VNIC Template %s to the list.',
                    value[1])
                vnic_template_info_list.append(
                    self.vnic_template_dict.get(key))
        return vnic_template_info_list

