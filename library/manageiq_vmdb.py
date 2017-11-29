#! /usr/bin/python
#
# (c) 2017, Drew Bomhof <dbomhof@redhat.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import (absolute_import, division, print_function)
import os

__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
module: manageiq_vmdb
'''
from ansible.module_utils.basic import AnsibleModule


try:
    from manageiq_client.api import ManageIQClient
    HAS_CLIENT = True
except ImportError:
    HAS_CLIENT = False


def check_client(module):
    if not HAS_CLIENT:
        module.fail_json(msg='manageiq_client.api is required for this module')


def validate_connection_params(module):
    params = module.params['manageiq_connection']
    error_str = "missing required argument: manageiq_connection[{}]"
    url = params['url']
    token = params.get('token')
    username = params.get('username')
    password = params.get('password')

    if (url and username and password) or (url and token):
        return params
    for arg in ['url', 'username', 'password']:
        if params[arg] in (None, ''):
            module.fail_json(msg=error_str.format(arg))


class ManageIQ(object):
    """
        class encapsulating ManageIQ API client.
    """

    def __init__(self, module):
        # handle import errors
        check_client(module)
        params = validate_connection_params(module)

        url = params['url']
        username = params.get('username')
        password = params.get('password')
        token = params.get('token')
        verify_ssl = params.get('verify_ssl')
        ca_bundle_path = params.get('ca_bundle_path')

        self._module = module
        self._api_url = url + '/api'
        self._auth = dict(user=username, password=password, token=token)
        try:
            self._client = ManageIQClient(self._api_url, self._auth, verify_ssl=verify_ssl, ca_bundle_path=ca_bundle_path)
        except Exception as e:
            self.module.fail_json(msg="failed to open connection (%s): %s" % (url, str(e)))

    @property
    def module(self):
        """ Ansible module module

        Returns:
            the ansible module
        """
        return self._module

    @property
    def api_url(self):
        """ Base ManageIQ API

        Returns:
            the base ManageIQ API
        """
        return self._api_url

    @property
    def client(self):
        """ ManageIQ client

        Returns:
            the ManageIQ client
        """
        return self._client


class ManageIQVmdb(object):
    """
        Object to execute VMDB management operations in manageiq.
    """

    def __init__(self, manageiq):
        self._manageiq = manageiq
        self._module = self._manageiq.module
        self._api_url = self._manageiq.api_url
        self._vmdb = self._module.params.get('vmdb') or self._module.params.get('href')
        self._href = None
        self._client = self._manageiq.client
        self._error = None


    @property
    def url(self):
        """
            The url to connect to the VMDB Object
        """
        return self._api_url

    @property
    def post_url(self):
        """
            The url to connect to the vmdb
        """
        if self._href:
            return self._api_url + '/' + self._href
        return self._api_url


    def get(self, alt_url=None):
        """
            Get any attribute, object from the REST API
        """
        if alt_url:
            url = alt_url
        else:
            url = self.url
        result = self._client.get(url)
        return dict(result)


    def parse(self, item):
        """
            Read what is passed in and set the _href instance variable
        """
        if isinstance(item, dict):
            self._api_url = self._vmdb['href']
        elif isinstance(item, str):
            slug = item.split("::")
            if len(slug) == 2:
                self._href = slug[1]
                return
            self._href = item


    def exists(self, path):
        """
            Validate all passed objects before attempting to set or get values from them
        """
        result = self.get(self.post_url)
        actions = [d['name'] for d in result['actions']]
        return bool(path in actions)


class Vmdb(ManageIQVmdb):
    """
        Object to modify and get the Vmdb Object
    """

    def get_object(self):
        """
            Return the VMDB Object
        """
        self.parse(self._vmdb)
        return dict(self.get(self.post_url))


    def action(self):
        """
            Call an action if it exists
        """
        self.parse(self._vmdb)
        data = self._module.params['data']
        action_string = self._module.params.get('action')

        if self.exists(action_string):
            result = self._client.post(self.post_url, action=action_string, resource=data)
            if result['success']:
                return dict(changed=False, value=result)
            return self._module.fail_json(msg=result['message'])
        return self._module.fail_json(msg="Action not found")


def manageiq_argument_spec():
    return dict(
        url=dict(default=os.environ.get('MIQ_URL', None)),
        username=dict(default=os.environ.get('MIQ_USERNAME', None)),
        password=dict(default=os.environ.get('MIQ_PASSWORD', None), no_log=True),
        token=dict(default=os.environ.get('MIQ_TOKEN', None), no_log=True),
        automate_workspace=dict(default=None, type='str', no_log=True),
        group=dict(default=None, type='str'),
        X_MIQ_Group=dict(default=None, type='str'),
        verify_ssl=dict(default=True, type='bool'),
        ca_bundle_path=dict(required=False, default=None),
    )


def main():
    """
        The entry point to the ManageIQ Vmdb module
    """
    module = AnsibleModule(
            argument_spec=dict(
                manageiq_connection=dict(required=True, type='dict',
                                         options=manageiq_argument_spec()),
                vmdb=dict(required=False, type='dict'),
                action=dict(required=False, type='str'),
                href=dict(required=False, type='str'),
                data=dict(required=False, type='dict')
                ),
            required_one_of=[['vmdb', 'href']]
            )


    manageiq = ManageIQ(module)
    vmdb = Vmdb(manageiq)

    if module.params.get('action'):
        result = vmdb.action()
        module.exit_json(**result)
    else:
        result = vmdb.get_object()
        module.exit_json(**result)

    module.fail_json(msg="No VMDB object found")


if __name__ == "__main__":
    main()
