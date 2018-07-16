#    Copyright 2014, Cisco Systems.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""
Common functionalities shared between different UCS modules.
"""

def create_dn_in_filter(ucsmsdk, filter_class, filter_value):
    """ Creates filter object for given class name, and DN values."""
    in_filter = ucsmsdk.FilterFilter()
    in_filter.AddChild(create_dn_wcard_filter(ucsmsdk, filter_class, filter_value))
    return in_filter


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
