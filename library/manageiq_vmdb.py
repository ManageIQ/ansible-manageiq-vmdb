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
import json
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url

class ManageIQVmdb(object):
    """
        Object to execute VMDB management operations in manageiq.
    """

    def __init__(self, module):
        self._module = module
        self._api_url = self._module.params['manageiq_connection']['url'] + '/api'
        self._vmdb = self._module.params.get('vmdb') or self._module.params.get('href')
        self._href = None
        self._error = None
        self._auth = self._build_auth()


    def _build_auth(self):
        self._headers = {'Content-Type': 'application/json; charset=utf-8'}
        # Force CERT validation to work with fetch_url
        self._module.params['validate_certs'] = self._module.params['manageiq_connection']['manageiq_validate_certs']
        for cert in ('force_basic_auth', 'client_cert', 'client_key'):
            self._module.params[cert] = self._module.params['manageiq_connection'][cert]
        if self._module.params['manageiq_connection'].get('token'):
            self._headers["X-Auth-Token"] = self._module.params['manageiq_connection']['token']
        else:
            self._module.params['url_username'] = self._module.params['manageiq_connection']['username']
            self._module.params['url_password'] = self._module.params['manageiq_connection']['password']




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
        result, _info = fetch_url(self._module, url, None, self._headers, 'get')
        return json.loads(result.read())


    def set(self, post_dict):
        """
            Set any attribute, object from the REST API
        """
        post_data = json.dumps(dict(action=post_dict['action'], resource=post_dict['resource']))
        result, _info = fetch_url(self._module, self.url, post_data, self._headers, 'post')
        return  json.loads(result.read())


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
        # Need to validate all urls that come in
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
            result = self.set(dict(action=action_string, resource=data))
            if result['success']:
                return dict(changed=True, value=result)
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
        manageiq_validate_certs=dict(required=False, type='bool', default=True),
        force_basic_auth=dict(required=False, type='bool', default='no'),
        client_cert=dict(required=False, type='path', default=None),
        client_key=dict(required=False, type='path', default=None)
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


    vmdb = Vmdb(module)

    if module.params.get('action'):
        result = vmdb.action()
        module.exit_json(**result)
    else:
        result = vmdb.get_object()
        module.exit_json(**result)

    module.fail_json(msg="No VMDB object found")


if __name__ == "__main__":
    main()
