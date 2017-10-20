"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, October 19th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import socket
import hashlib

from acmd import packet

class ProtocolEstablishConnectionRequest(packet.Packet):
    DIRECTION = packet.PacketDirections.UPSTREAM
    ID = 0x00

    async def serialize(self):
        data_buffer = packet.PacketDataBuffer()
        data_buffer.pack_bytes(socket.inet_aton(self._handler.address))

        return data_buffer

class ProtocolEstablishConnection(packet.Packet):
    DIRECTION = packet.PacketDirections.DOWNSTREAM
    ID = 0x00

    async def deserialize(self, data_buffer):
        try:
            address_bits = data_buffer.unpack_bytes()
        except:
            return await self._handler.handle_disconnect()

        if self._handler.factory.address != socket.inet_ntoa(address_bits):
            return await self._handler.handle_disconnect()

    async def deserialize_callback(self):
        await self._dispatcher.handle_dispatch_packet(ProtocolEstablishCrypto)

class ProtocolEstablishCrypto(packet.Packet):
    DIRECTION = packet.PacketDirections.UPSTREAM
    ID = 0x01

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.key = None

    async def serialize(self):
        self.key = self._handler._encryptor.generate_key()

        data_buffer = packet.PacketDataBuffer()
        data_buffer.pack_bytes(self.key)

        return data_buffer

    async def serialize_callback(self):
        if not self.key:
            return await self._handler.handle_disconnect()

        self._handler._encryptor.setup_crypto(self.key)
        self.key = None

class ProtocolEstablishCryptoResponse(packet.Packet):
    DIRECTION = packet.PacketDirections.DOWNSTREAM
    ID = 0x01

    async def deserialize(self, data_buffer):
        try:
            key = data_buffer.unpack_bytes()
        except:
            return self._handler.handle_disconnect()

        self._handler._encryptor.setup_crypto(key)

class ProtocolDispatcher(packet.PacketDispatcher):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_packet(ProtocolEstablishConnectionRequest)
        self.add_packet(ProtocolEstablishConnection)

        self.add_packet(ProtocolEstablishCrypto)
        self.add_packet(ProtocolEstablishCryptoResponse)
