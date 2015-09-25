#!/usr/bin/env python
#
# Copyright 2015-2015 breakwa11
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, \
    with_statement

import os
import sys
import hashlib
import logging
import binascii
import base64
import datetime
from shadowsocks.common import to_bytes, to_str

def create_http_obfs(method):
    return http_simple(method)

def create_http2_obfs(method):
    return http2_simple(method)

obfs = {
        'http_simple': (create_http_obfs,),
        'http2_simple': (create_http2_obfs,),
}

def match_begin(str1, str2):
    if len(str1) >= len(str2):
        if str1[:len(str2)] == str2:
            return True
    return False

class http_simple(object):
    def __init__(self, method):
        self.method = method
        self.has_sent_header = False
        self.has_recv_header = False
        self.host = None
        self.port = 0
        self.recv_buffer = b''

    def client_encode(self, buf):
        # TODO
        return buf

    def client_decode(self, buf):
        # TODO
        return (buf, False)

    def server_encode(self, buf):
        if self.has_sent_header:
            return buf
        else:
            header = b'HTTP/1.1 200 OK\r\nServer: openresty\r\nDate: '
            header += to_bytes(datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))
            header += b'\r\nContent-Type: text/plain; charset=utf-8\r\nTransfer-Encoding: chunked\r\nConnection: keep-alive\r\nKeep-Alive: timeout=20\r\nVary: Accept-Encoding\r\nContent-Encoding: gzip\r\n\r\n'
            self.has_sent_header = True
            return header + buf

    def get_data_from_http_header(self, buf):
        ret_buf = b''
        lines = buf.split(b'\r\n')
        if lines and len(lines) > 4:
            hex_items = lines[0].split(b'%')
            if hex_items and len(hex_items) > 1:
                for index in range(1, len(hex_items)):
                    if len(hex_items[index]) != 2:
                        ret_buf += binascii.unhexlify(hex_items[index][:2])
                        break
                    ret_buf += binascii.unhexlify(hex_items[index])
                return ret_buf
        return b''

    def server_decode(self, buf):
        if self.has_recv_header:
            return (buf, True, False)
        else:
            buf = self.recv_buffer + buf
            if len(buf) > 10:
                if match_begin(buf, b'GET /') or match_begin(buf, b'POST /'):
                    pass
                else: #not http header, run on original protocol
                    self.has_sent_header = True
                    self.has_recv_header = True
                    self.recv_buffer = None
                    return (buf, True, False)
            else:
                self.recv_buffer = buf
                return (b'', True, False)

            datas = buf.split(b'\r\n\r\n', 1)
            ret_buf = b''
            if datas and len(datas) > 1:
                ret_buf = self.get_data_from_http_header(buf)
                ret_buf += datas[1]
                if len(ret_buf) >= 15:
                    self.has_recv_header = True
                    return (ret_buf, True, False)
                self.recv_buffer = buf
                return (b'', True, False)
            else:
                self.recv_buffer = buf
                return (b'', True, False)
            self.has_sent_header = True
            self.has_recv_header = True
            return (buf, True, False)

class http2_simple(object):
    def __init__(self, method):
        self.method = method
        self.has_sent_header = False
        self.has_recv_header = False
        self.host = None
        self.port = 0
        self.recv_buffer = b''

    def client_encode(self, buf):
        # TODO
        return buf

    def client_decode(self, buf):
        # TODO
        return (buf, False)

    def server_encode(self, buf):
        if self.has_sent_header:
            return buf
        else:
            header = b'HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\nUpgrade: h2c\r\n\r\n'
            self.has_sent_header = True
            return header + buf

    def server_decode(self, buf):
        if self.has_recv_header:
            return (buf, True, False)
        else:
            buf = self.recv_buffer + buf
            if len(buf) > 10:
                if match_begin(buf, b'GET /'):
                    pass
                else: #not http header, run on original protocol
                    self.has_sent_header = True
                    self.has_recv_header = True
                    self.recv_buffer = None
                    return (buf, True, False)
            else:
                self.recv_buffer = buf
                return (b'', True, False)

            datas = buf.split(b'\r\n\r\n', 1)
            if datas and len(datas) > 1 and len(datas[0]) >= 4:
                lines = buf.split(b'\r\n')
                if lines and len(lines) >= 4:
                    if match_begin(lines[4], b'HTTP2-Settings: '):
                        ret_buf = base64.urlsafe_b64decode(lines[4][16:])
                        ret_buf += datas[1]
                        self.has_recv_header = True
                        return (ret_buf, True, False)
                self.recv_buffer = buf
                return (b'', True, False)
            else:
                self.recv_buffer = buf
                return (b'', True, False)
            self.has_sent_header = True
            self.has_recv_header = True
            return (buf, True, False)
