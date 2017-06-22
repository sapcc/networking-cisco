# Copyright 2014 Cisco Systems, Inc.  All rights reserved.
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

import logging

LOG = logging.getLogger(__name__)

ALERT_PREFIX = 'asr:alert_level:%s message:%s detail:%s'
ALERT_CRITICAL = 'CRITICAL'
ALERT_WARNING = 'WARNING'
ALERT_INFO = 'INFO'



class AlertMixin():


    def emit_alert(self,level, message, detail=""):
        LOG.error(ALERT_PREFIX, level, message, detail)
