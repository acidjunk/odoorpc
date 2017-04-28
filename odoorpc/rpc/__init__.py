# -*- coding: UTF-8 -*-
##############################################################################
#
#    OdooRPC
#    Copyright (C) 2014 Sébastien Alix.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""This module provides `Connector` classes to communicate with an `Odoo`
server with the `JSON-RPC` protocol or through simple HTTP requests.

Web controllers of `Odoo` expose two kinds of methods: `json` and `http`.
These methods can be accessed from the connectors of this module.
"""
import sys
# Python 2
if sys.version_info[0] < 3:
    from urllib2 import build_opener, HTTPCookieProcessor
    from cookielib import CookieJar
# Python >= 3
else:
    from urllib.request import build_opener, HTTPCookieProcessor
    from http.cookiejar import CookieJar

from odoorpc.rpc import error, jsonrpclib
from odoorpc.tools import v


class Connector(object):
    """Connector base class defining the interface used
    to interact with a server.
    """
    def __init__(self, host, port=8069, timeout=120, version=None):
        self.host = host
        try:
            int(port)
        except ValueError:
            txt = "The port '{0}' is invalid. An integer is required."
            txt = txt.format(port)
            raise error.ConnectorError(txt)
        else:
            self.port = int(port)
        self._timeout = timeout
        self.version = version

    @property
    def ssl(self):
        """Return `True` if SSL is activated."""
        return False

    @property
    def timeout(self):
        """Return the timeout."""
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        """Set the timeout."""
        self._timeout = timeout


class ConnectorJSONRPC(Connector):
    """Connector class using the `JSON-RPC` protocol.

    .. doctest::
        :options: +SKIP

        >>> from odoorpc import rpc
        >>> cnt = rpc.ConnectorJSONRPC('localhost', port=8069)

    .. doctest::
        :hide:

        >>> from odoorpc import rpc
        >>> cnt = rpc.ConnectorJSONRPC(HOST, port=PORT)

    Open a user session:

    .. doctest::
        :options: +SKIP

        >>> cnt.proxy_json.web.session.authenticate(db='db_name', login='admin', password='password')
        {'id': 51373612,
         'jsonrpc': '2.0',
         'result': {'company_id': 1,
                    'currencies': {'1': {'digits': [69, 2],
                                         'position': 'after',
                                         'symbol': '\u20ac'},
                                   '3': {'digits': [69, 2],
                                         'position': 'before',
                                         'symbol': '$'}},
                    'db': 'db_name',
                    'is_admin': True,
                    'is_superuser': True,
                    'name': 'Administrator',
                    'partner_id': 3,
                    'server_version': '10.0',
                    'server_version_info': [10, 0, 0, 'final', 0, ''],
                    'session_id': '6dd7a34f16c1c67b38bfec413cca4962d5c01d53',
                    'uid': 1,
                    'user_companies': False,
                    'user_context': {'lang': 'en_US',
                                     'tz': 'Europe/Brussels',
                                     'uid': 1},
                    'username': 'admin',
                    'web.base.url': 'http://localhost:8069',
                    'web_tours': []}}

    .. doctest::
        :hide:
        :options: +NORMALIZE_WHITESPACE

        >>> from odoorpc.tools import v
        >>> data = cnt.proxy_json.web.session.authenticate(db=DB, login=USER, password=PWD)
        >>> keys = ['company_id', 'db', 'session_id', 'uid', 'user_context', 'username']
        >>> if v(VERSION) >= v('10.0'):
        ...     keys.extend([
        ...         'currencies', 'is_admin', 'is_superuser', 'name',
        ...         'partner_id', 'server_version', 'server_version_info',
        ...         'user_companies', 'web.base.url', 'web_tours',
        ...     ])
        >>> all([key in data['result'] for key in keys])
        True

    Read data of a partner:

    .. doctest::
        :options: +SKIP

        >>> cnt.proxy_json.web.dataset.call(model='res.partner', method='read', args=[[1]])
        {'jsonrpc': '2.0', 'id': 454236230,
         'result': [{'id': 1, 'comment': False, 'ean13': False, 'property_account_position': False, ...}]}

    .. doctest::
        :hide:

        >>> data = cnt.proxy_json.web.dataset.call(model='res.partner', method='read', args=[[1]])
        >>> 'jsonrpc' in data and 'id' in data and 'result' in data
        True

    You can send requests this way too:

    .. doctest::
        :options: +SKIP

        >>> cnt.proxy_json['/web/dataset/call'](model='res.partner', method='read', args=[[1]])
        {'jsonrpc': '2.0', 'id': 328686288,
         'result': [{'id': 1, 'comment': False, 'ean13': False, 'property_account_position': False, ...}]}

    .. doctest::
        :hide:

        >>> data = cnt.proxy_json['/web/dataset/call'](model='res.partner', method='read', args=[[1]])
        >>> 'jsonrpc' in data and 'id' in data and 'result' in data
        True

    Or like this:

    .. doctest::
        :options: +SKIP

        >>> cnt.proxy_json['web']['dataset']['call'](model='res.partner', method='read', args=[[1]])
        {'jsonrpc': '2.0', 'id': 102320639,
         'result': [{'id': 1, 'comment': False, 'ean13': False, 'property_account_position': False, ...}]}

    .. doctest::
        :hide:

        >>> data = cnt.proxy_json['web']['dataset']['call'](model='res.partner', method='read', args=[[1]])
        >>> 'jsonrpc' in data and 'id' in data and 'result' in data
        True
    """
    def __init__(self, host, port=8069, timeout=120, version=None,
                 deserialize=True, opener=None):
        super(ConnectorJSONRPC, self).__init__(host, port, timeout, version)
        self.deserialize = deserialize
        # One URL opener (with cookies handling) shared between
        # JSON and HTTP requests
        if opener is None:
            cookie_jar = CookieJar()
            opener = build_opener(
                HTTPCookieProcessor(cookie_jar))
        self._opener = opener
        self._proxy_json, self._proxy_http = self._get_proxies()

    def _get_proxies(self):
        """Returns the :class:`ProxyJSON <odoorpc.rpc.jsonrpclib.ProxyJSON>`
        and :class:`ProxyHTTP <odoorpc.rpc.jsonrpclib.ProxyHTTP>` instances
        corresponding to the server version used.
        """
        proxy_json = jsonrpclib.ProxyJSON(
            self.host, self.port, self._timeout,
            ssl=self.ssl, deserialize=self.deserialize, opener=self._opener)
        proxy_http = jsonrpclib.ProxyHTTP(
            self.host, self.port, self._timeout,
            ssl=self.ssl, opener=self._opener)
        # Detect the server version
        if self.version is None:
            try:
                result = proxy_json.web.webclient.version_info()['result']
                if 'server_version' in result:
                    self.version = result['server_version']
            except:
                pass
        return proxy_json, proxy_http

    @property
    def proxy_json(self):
        """Return the JSON proxy."""
        return self._proxy_json

    @property
    def proxy_http(self):
        """Return the HTTP proxy."""
        return self._proxy_http

    @property
    def timeout(self):
        """Return the timeout."""
        return self._proxy_json._timeout

    @timeout.setter
    def timeout(self, timeout):
        """Set the timeout."""
        self._proxy_json._timeout = timeout
        self._proxy_http._timeout = timeout


class ConnectorJSONRPCSSL(ConnectorJSONRPC):
    """Connector class using the `JSON-RPC` protocol over `SSL`.

    .. doctest::
        :options: +SKIP

        >>> from odoorpc import rpc
        >>> cnt = rpc.ConnectorJSONRPCSSL('localhost', port=8069)

    .. doctest::
        :hide:

        >>> if 'ssl' in PROTOCOL:
        ...     from odoorpc import rpc
        ...     cnt = rpc.ConnectorJSONRPCSSL(HOST, port=PORT)
    """
    def __init__(self, host, port=8069, timeout=120, version=None,
                 deserialize=True, opener=None):
        super(ConnectorJSONRPCSSL, self).__init__(
            host, port, timeout, version, opener=opener)
        self._proxy_json, self._proxy_http = self._get_proxies()

    @property
    def ssl(self):
        return True


PROTOCOLS = {
    'jsonrpc': ConnectorJSONRPC,
    'jsonrpc+ssl': ConnectorJSONRPCSSL,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
