"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, October 19th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import os
import zlib
import hashlib

from Crypto import Random
from Crypto.Cipher import AES

from curionet import network
from acmd import packet, protocol

class NetworkIOEncryptorError(RuntimeError):
    """
    A network io encryptor specific runtime error
    """

class NetworkIOEncryptor(object):
    """
    Network data encryptor, handles incoming/outgoing data encryption and compression
    """

    COMPRESSION_LEVEL = 9

    def __init__(self):
        self._crypto = None

    def generate_key(self, length=16):
        """
        Generates a new AES crypto key for data encryption over the network
        """

        # generate a new random key using the operating system (depends on os implementation...)
        new_key = os.urandom(length)

        # hash the newly generated key to ensure it's unique...
        return hashlib.sha256(new_key).digest()

    def setup_crypto(self, key, iv=None):
        """
        Sets up a new crypto for AES using key and iv
        """

        self._crypto = AES.new(key, AES.MODE_CFB, iv or Random.new().read(AES.block_size))

    def encrypt(self, data):
        if self._crypto:
            data = self._crypto.encrypt(data)

        return zlib.compress(data, self.COMPRESSION_LEVEL)

    def decrypt(self, data):
        if self._crypto:
            data = self._crypto.decrypt(data)

        return zlib.decompress(data)

class NetworkIOHandler(network.NetworkHandler):
    """
    Network connection session handler
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._dispatcher = protocol.ProtocolDispatcher(self)
        self._encryptor = NetworkIOEncryptor()

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def encryptor(self):
        return self._encryptor

    async def handle_connected(self):
        pass

    async def handle_received(self, data):
        data_buffer = packet.PacketDataBuffer(self._encryptor.decrypt(data))

        if not data_buffer.data:
            return await self.handle_disconnect()

        try:
            packet_length = data_buffer.unpack_ushort()
        except:
            return await self.handle_disconnect()

        if not packet_length:
            return await self.handle_disconnect()

        await self.handle_incoming_packet(packet.PacketDataBuffer(data_buffer.read(packet_length)))

    async def handle_incoming_packet(self, data_buffer):
        try:
            packet_id = data_buffer.unpack_ushort()
        except:
            return await self.handle_disconnect()

        await self._dispatcher.handle_dispatch(packet.PacketDirections.DOWNSTREAM, packet_id,
            data_buffer)

    async def handle_disconnected(self):
        pass

class NetworkIOFactory(network.NetworkFactory):
    """
    Network factory for managing network sessions
    """

    async def handle_start(self):
        pass

    async def handle_stop(self):
        pass

class NetworkIOConnector(network.NetworkConnector):
    """
    Network connector for connecting to a network factory
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._dispatcher = protocol.ProtocolDispatcher(self)
        self._encryptor = NetworkIOEncryptor()

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def encryptor(self):
        return self._encryptor

    async def handle_connected(self):
        await self._dispatcher.handle_dispatch_packet(protocol.ProtocolEstablishConnectionRequest)

    async def handle_received(self, data):
        data_buffer = packet.PacketDataBuffer(self._encryptor.decrypt(data))

        if not data_buffer.data:
            return await self.handle_disconnect()

        try:
            packet_length = data_buffer.unpack_ushort()
        except:
            return await self.handle_disconnect()

        if not packet_length:
            return await self.handle_disconnect()

        await self.handle_incoming_packet(packet.PacketDataBuffer(data_buffer.read(packet_length)))

    async def handle_incoming_packet(self, data_buffer):
        try:
            packet_id = data_buffer.unpack_ushort()
        except:
            return await self.handle_disconnect()

        await self._dispatcher.handle_dispatch(packet.PacketDirections.DOWNSTREAM, packet_id,
            data_buffer)

    async def handle_disconnected(self):
        pass
