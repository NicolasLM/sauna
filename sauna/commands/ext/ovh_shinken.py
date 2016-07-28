# Copyright (c) 2013-2016, OVH SAS.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#  * Neither the name of OVH SAS nor the
#    names of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY OVH SAS AND CONTRIBUTORS ````AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL OVH SAS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
This module provides a simple python wrapper over the OVH REST API.
It handles requesting credential, signing queries...

 - To get your API keys: https://eu.api.ovh.com/createApp/
 - To get started with API: https://api.ovh.com/g934.first_step_with_api
"""

import hashlib
import keyword
import time
import json
from urllib.parse import urlencode
from copy import deepcopy

from sauna.commands import CommandRegister

#: Mapping between OVH API region names and corresponding endpoints
ENDPOINTS = {
    'ovh-eu': 'https://eu.api.ovh.com/1.0',
    'ovh-ca': 'https://ca.api.ovh.com/1.0',
    'kimsufi-eu': 'https://eu.api.kimsufi.com/1.0',
    'kimsufi-ca': 'https://ca.api.kimsufi.com/1.0',
    'soyoustart-eu': 'https://eu.api.soyoustart.com/1.0',
    'soyoustart-ca': 'https://ca.api.soyoustart.com/1.0',
    'runabove-ca': 'https://api.runabove.com/1.0',
}

#: Default timeout for each request. 180 seconds connect, 180 seconds read.
TIMEOUT = 180

# Common authorization patterns
API_READ_ONLY = ["GET"]
API_READ_WRITE = ["GET", "POST", "PUT", "DELETE"]
API_READ_WRITE_SAFE = ["GET", "POST", "PUT"]


class ConsumerKeyRequest(object):
    def __init__(self, client):
        self._client = client
        self._access_rules = []

    def request(self, redirect_url=None):
        return self._client.request_consumerkey(self._access_rules,
                                                redirect_url)

    def add_rule(self, method, path):
        self._access_rules.append({'method': method.upper(), 'path': path})

    def add_rules(self, methods, path):
        for method in methods:
            self.add_rule(method, path)

    def add_recursive_rules(self, methods, path):
        path = path.rstrip('*/ ')
        if path:
            self.add_rules(methods, path)
        self.add_rules(methods, path+'/*')


class Client(object):
    def __init__(self, endpoint=None, application_key=None,
                 application_secret=None, consumer_key=None, timeout=TIMEOUT):
        from requests import Session
        from requests.adapters import HTTPAdapter

        self._endpoint = ENDPOINTS[endpoint]
        self._application_key = application_key
        self._application_secret = application_secret
        self._consumer_key = consumer_key

        # lazy load time delta
        self._time_delta = None

        try:
            # Some older versions of requests to not have the urllib3
            # vendorized package
            from requests.packages.urllib3.util.retry import Retry
        except ImportError:
            retries = 5
        else:
            # use a requests session to reuse connections between requests
            retries = Retry(
                total=5,
                backoff_factor=0.2,
                status_forcelist=[422, 500, 502, 503, 504]
            )

        self._session = Session()
        self._session.mount('https://', HTTPAdapter(max_retries=retries))
        self._session.mount('http://', HTTPAdapter(max_retries=retries))

        # Override default timeout
        self._timeout = timeout

    @property
    def time_delta(self):
        if self._time_delta is None:
            server_time = self.get('/auth/time', _need_auth=False).json()
            self._time_delta = server_time - int(time.time())
        return self._time_delta

    def new_consumer_key_request(self):
        return ConsumerKeyRequest(self)

    def request_consumerkey(self, access_rules, redirect_url=None):
        res = self.post('/auth/credential', _need_auth=False,
                        accessRules=access_rules, redirection=redirect_url)
        self._consumer_key = res.json()['consumerKey']
        return res

    def _canonicalize_kwargs(self, kwargs):
        arguments = {}

        for k, v in kwargs.items():
            if k[0] == '_' and k[1:] in keyword.kwlist:
                k = k[1:]
            arguments[k] = v

        return arguments

    def get(self, _target, _need_auth=True, **kwargs):
        if kwargs:
            kwargs = self._canonicalize_kwargs(kwargs)
            query_string = urlencode(kwargs)
            if '?' in _target:
                _target = '%s&%s' % (_target, query_string)
            else:
                _target = '%s?%s' % (_target, query_string)

        return self.call('GET', _target, None, _need_auth)

    def put(self, _target, _need_auth=True, **kwargs):
        kwargs = self._canonicalize_kwargs(kwargs)
        return self.call('PUT', _target, kwargs, _need_auth)

    def post(self, _target, _need_auth=True, **kwargs):
        kwargs = self._canonicalize_kwargs(kwargs)
        return self.call('POST', _target, kwargs, _need_auth)

    def delete(self, _target, _need_auth=True):
        return self.call('DELETE', _target, None, _need_auth)

    def call(self, method, path, data=None, need_auth=True):
        body = ''
        target = self._endpoint + path
        headers = {
            'X-Ovh-Application': self._application_key
        }

        # include payload
        if data is not None:
            headers['Content-type'] = 'application/json'
            body = json.dumps(data)

        # sign request. Never sign 'time' or will recuse infinitely
        if need_auth:
            if not self._application_secret:
                raise Exception("Invalid ApplicationSecret '%s'" %
                                self._application_secret)

            if not self._consumer_key:
                raise Exception("Invalid ConsumerKey '%s'" %
                                self._consumer_key)

            now = str(int(time.time()) + self.time_delta)
            signature = hashlib.sha1()
            signature.update("+".join([
                self._application_secret, self._consumer_key,
                method.upper(), target,
                body,
                now
            ]).encode('utf-8'))

            headers['X-Ovh-Consumer'] = self._consumer_key
            headers['X-Ovh-Timestamp'] = now
            headers['X-Ovh-Signature'] = "$1$" + signature.hexdigest()

        response = self._session.request(method, target, headers=headers,
                                         data=body, timeout=self._timeout)
        response.raise_for_status()
        return response


def request_ovh_client(consumer_key=None):
    try:
        import requests
        import requests.exceptions
    except ImportError:
        print('The requests library is needed to perform this command:')
        print('    pip install requests')
        print('    apt-get install python3-requests')
        exit(1)
    client = Client(
        endpoint='ovh-eu',
        application_key='yVPsINnSdHOLTGHf',
        application_secret='5mVDkHaJw6rp5GYiYBUlgDv1vruRejkl',
        consumer_key=consumer_key
    )
    if not consumer_key:
        response = client.request_consumerkey(
            access_rules=[
                {'method': 'GET', 'path': '/paas/monitoring'},
                {'method': 'GET', 'path': '/paas/monitoring/*'},
                {'method': 'POST', 'path': '/paas/monitoring/*'},
                {'method': 'PUT', 'path': '/paas/monitoring/*'},
                {'method': 'DELETE', 'path': '/paas/monitoring/*'}
            ]
        )
        response = response.json()
        print('New consumer key:', response['consumerKey'])
        print('Validate it at', response['validationUrl'])
        input('When you are ready, press Enter')
    try:
        client.get('/paas/monitoring')
    except requests.exceptions.HTTPError as e:
        if not e.response.status_code == 403:
            raise
        return request_ovh_client()

    return client


def find_host_resource(client, shinken_id, hostname):
    hosts = client.get(
        '/paas/monitoring/{}/resource/host'.format(shinken_id)
    ).json()
    for host in hosts:
        host = client.get('/paas/monitoring/{}/resource/host/{}'.format(
            shinken_id, host
        )).json()
        for config_entry in host['config']:
            if (config_entry['key'] == 'host_name' and
                    config_entry['value'] == hostname):
                return host
    return None


def find_resources(client, shinken_id, resource_type, key, values):
    base_url = '/paas/monitoring/{}/resource/{}'.format(shinken_id,
                                                        resource_type)
    found = list()
    not_found = deepcopy(values)
    for resource_id in client.get(base_url).json():
        resource = client.get('{}/{}'.format(
            base_url, resource_id
        )).json()
        for config_entry in resource['config']:
            if (config_entry['key'] == key and
                    config_entry['value'] in not_found):
                found.append(resource)
                not_found.remove(config_entry['value'])
                break

        if not not_found:
            break

    return found, not_found


def find_default_ip_address():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('198.27.92.1', 80))
    return s.getsockname()[0]


def create_hostgroup_resource(client, shinken_id, hostgroup):
    base_url = '/paas/monitoring/{}/resource/hostgroup'.format(shinken_id)
    client.call('POST', base_url, {
        'config': [
            {'key': 'hostgroup_name', 'value': hostgroup}
        ]
    })


def create_host_resource(client, shinken_id, hostname, ip_address,
                         hostgroup, template):
    base_url = '/paas/monitoring/{}/resource/host'.format(shinken_id)
    client.call('POST', base_url, {
        'config': [
            {'key': 'host_name', 'value': hostname},
            {'key': 'address', 'value': ip_address},
            {'key': 'hostgroups', 'value': hostgroup},
            {'key': 'use', 'value': template}
        ]
    })


def create_service_resource(client, shinken_id, service_name, hostgroup,
                            template):
    base_url = '/paas/monitoring/{}/resource/service'.format(shinken_id)
    client.call('POST', base_url, {
        'config': [
            {'key': 'service_description', 'value': service_name},
            {'key': 'hostgroups', 'value': hostgroup},
            {'key': 'use', 'value': template}
        ]
    })


def synchronize_services(client, shinken_id, services, hostgroup):
    base_url = '/paas/monitoring/{}/resource/service'.format(shinken_id)
    for resource in services:
        for config_entry in resource['config']:
            if (config_entry['key'] == 'hostgroups'):
                if hostgroup not in config_entry['value']:
                    config_entry['value'] += ', {}'.format(hostgroup)
                    client.call(
                        'PUT',
                        '{}/{}'.format(base_url, resource['id']),
                        {'config': resource['config']}
                    )


def verify_shinken_nsca(client, shinken_id, sauna_config):
    nsca_config = client.get('/paas/monitoring/{}/config/nsca'.
                             format(shinken_id)).json()
    shinken_hostname = client.get('/paas/monitoring/{}'.
                                  format(shinken_id)).json()['hostname']
    needed_encryption = nsca_config['encryption']
    needed_key = nsca_config['key']
    needed_receiver = 'receiver.' + shinken_hostname

    if not nsca_config['enabled']:
        print('Warning: NSCA is not enabled on your Shinken. Activate it in '
              'your OVH manager')
        return

    try:
        sauna_nsca_config = sauna_config['consumers']['NSCA']
    except KeyError:
        print('Warning: NSCA consumer is not enabled in sauna, add it'
              ' to your sauna.yml')
        return print_nsca_config(needed_receiver, needed_encryption,
                                 needed_key)

    if sauna_nsca_config.get('server', 'localhost') != needed_receiver:
        return print_nsca_config(needed_receiver, needed_encryption,
                                 needed_key)
    if sauna_nsca_config.get('encryption', 0) != needed_encryption:
        return print_nsca_config(needed_receiver, needed_encryption,
                                 needed_key)
    if sauna_nsca_config.get('key', '') != needed_key:
        return print_nsca_config(needed_receiver, needed_encryption,
                                 needed_key)


def print_nsca_config(receiver, encryption, key):
    yaml_config = '''
Your sauna.yml should include:

consumers:
  NSCA:
    server: {}
    encryption: {}
    key: {}
'''.format(receiver, encryption, key or '""')
    print(yaml_config)


command = CommandRegister()


@command.command(name='register')
def register_server(sauna_instance, args):
    """Register a server to OVH Shinken monitoring

    Usage:
      sauna register --hostgroup hostgroup [--ck consumerkey] [--shinken id]
      sauna register (-h | --help)

    Options:
      -h --help               Show this screen.
      --hostgroup=<hostgroup> Hostgroup of the server
      --ck=<consumerkey>      OVH API consumer key to use
      --shinken=<id>          OVH Shinken ID
    """
    hostgroup = args['--hostgroup']
    client = request_ovh_client(consumer_key=args['--ck'])
    shinken_id = args['--shinken'] or client.get('/paas/monitoring').json()[0]

    # Find and add hostgroup if needed
    found, not_found = find_resources(
        client, shinken_id, 'hostgroup', 'hostgroup_name', [hostgroup]
    )
    if not_found:
        print('Adding hostgroup', hostgroup)
        create_hostgroup_resource(client, shinken_id, hostgroup)
        print('done')
    else:
        print('Hostgroup', hostgroup, 'already exists')

    # Find and add host if needed
    found, not_found = find_resources(
        client, shinken_id, 'host', 'host_name', [sauna_instance.hostname]
    )
    if not_found:
        print('Adding host', sauna_instance.hostname)
        create_host_resource(client, shinken_id, sauna_instance.hostname,
                             find_default_ip_address(), hostgroup,
                             'generic-host')
        print('done')
    else:
        print('Host', sauna_instance.hostname, 'already exists')

    # Find and add services if needed
    found, not_found = find_resources(
        client, shinken_id, 'service', 'service_description',
        sauna_instance.get_active_checks_name()
    )
    if not_found:
        print('Adding services:', ', '.join(not_found))
        for service_name in not_found:
            create_service_resource(
                client, shinken_id, service_name, hostgroup,
                'passive-generic-service'
            )
    synchronize_services(client, shinken_id, found, hostgroup)
    print('All services are synchronized')

    verify_shinken_nsca(client, shinken_id, sauna_instance.config)

    print('Applying configuration by reloading Shinken')
    client.post('/paas/monitoring/{}/resource/apply'.format(shinken_id))
    print('done')
