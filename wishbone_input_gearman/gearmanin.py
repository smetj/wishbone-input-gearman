#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  gearmanin.py
#
#  Copyright 2016 Jelle Smet <development@smetj.net>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

from gevent import socket
import mock
from gevent import monkey; monkey.patch_all()
from wishbone import Actor
from wishbone.event import Event
from gevent import sleep
from gearman import GearmanWorker
from gearman.connection import GearmanConnection
from gearman import __version__ as gearman_version
from Crypto.Cipher import AES
import base64

def create_client_socket(self):
    """
    Patched version of gearman.connection.GearmanConnection._create_client_socket.
    This patched version returns sockets with TCP keepalive enabled.

    Creates a client side socket and subsequently binds/configures our socket options"""

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        client_socket.connect((self.gearman_host, self.gearman_port))
    except socket.error, socket_exception:
        self.throw_exception(exception=socket_exception)

    self.set_socket(client_socket)


class GearmanIn(Actor):

    '''**Consumes events/jobs from  Gearmand.**

    Consumes jobs from a Gearmand server.
    When secret is none, no decryption is done.


    Parameters:

        - hostlist(list)(["localhost:4730"])
           |  A list of gearmand servers.  Each entry should have
           |  format host:port.

        - secret(str)(None)
           |  The AES encryption key to decrypt Mod_gearman messages.

        - workers(int)(1)
           |  The number of gearman workers within 1 process.

        - queue(str)(wishbone)
           |  The queue to consume jobs from.

        - enable_keepalive(bool)(False)
           |  Attempt to monkey patch the gearmand module to enable socket
           |  keepalive.


    Queues:

        - outbox:   Outgoing events.

    '''

    def __init__(self, actor_config, hostlist=["localhost:4730"], secret=None, workers=1, queue="wishbone", enable_keepalive=False):
        Actor.__init__(self, actor_config)

        self.pool.createQueue("outbox")
        self.background_instances = []

        if self.kwargs.secret is None:
            self.decrypt = self.__plainTextJob
        else:
            key = self.kwargs.secret[0:32]
            self.cipher = AES.new(key + chr(0) * (32 - len(key)))
            self.decrypt = self.__encryptedJob

    def preHook(self):

        if self.kwargs.enable_keepalive:
            self.logging.info("Requested to monkey patch Gearmand")
            if gearman_version == "2.0.2":
                self.logging.info("Detected gearman version 2.0.2, patching sockets with SO_KEEPALIVE enabled.")
                self.gearmanWorker = self._gearmanWorkerPatched
            else:
                self.logging.warning("Did not detect gearman version 2.0.2. Not patching , patching sockets with keepalive enabled.")
                self.gearmanWorker = self._gearmanWorkerNotPatched
        else:
            self.gearmanWorker = self._gearmanWorkerNotPatched

        for _ in range(self.kwargs.workers):
            self.sendToBackground(self.gearmanWorker)

    def consume(self, gearman_worker, gearman_job):

        decrypted = self.decrypt(gearman_job.data)
        event = Event(decrypted)
        self.submit(event, self.pool.queue.outbox)
        return decrypted

    def __encryptedJob(self, data):
        return self.cipher.decrypt(base64.b64decode(data))

    def __plainTextJob(self, data):
        return data

    def _gearmanWorkerPatched(self):

        self.logging.info("Gearmand worker instance started")
        while self.loop():
            try:
                with mock.patch.object(GearmanConnection, '_create_client_socket', create_client_socket):
                    worker_instance = GearmanWorker(self.kwargs.hostlist)
                    worker_instance.register_task(self.kwargs.queue, self.consume)
                    worker_instance.work()
            except Exception as err:
                self.logging.warn('Connection to gearmand failed. Reason: %s. Retry in 1 second.' % err)
                sleep(1)

    def _gearmanWorkerNotPatched(self):

        self.logging.info("Gearmand worker instance started")
        while self.loop():
            try:
                worker_instance = GearmanWorker(self.kwargs.hostlist)
                worker_instance.register_task(self.kwargs.queue, self.consume)
                worker_instance.work()
            except Exception as err:
                self.logging.warn('Connection to gearmand failed. Reason: %s. Retry in 1 second.' % err)
                sleep(1)
