# Copyright 2015 Cisco Systems, Inc.
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

"""update_ha_group_primary_key

Revision ID: 13f45d65789d
Revises: 11ba2d65c8de
Create Date: 2015-11-26 23:33:41.877280

"""

# revision identifiers, used by Alembic.
revision = '13f45d65789d'
down_revision = '11ba2d65c8de'

from alembic import op


def upgrade():


    op.drop_constraint('cisco_router_ha_groups_pkey', 'cisco_router_ha_groups', type_='primary')
    op.create_primary_key(
        'cisco_router_ha_groups_pkey','cisco_router_ha_groups', ['ha_port_id', 'subnet_id'])

