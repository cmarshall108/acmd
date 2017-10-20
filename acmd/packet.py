"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, October 19th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import struct

class PacketDirections(object):
    UPSTREAM = 0
    DOWNSTREAM = 1

class PacketDataBufferError(RuntimeError):
    """
    A packet data buffer specific runtime error
    """

class PacketDataBuffer(object):
    """
    A packet data buffer for reading and writing data
    """

    ENDIANNESS = '!'

    def __init__(self, data=bytes(), offset=0):
        self._data = data
        self._offset = offset

    @property
    def data(self):
        return self._data

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, offset):
        self._offset = offset

    def write(self, data):
        if not data:
            raise PacketDataBufferError('Cannot write null bytes to buffer!')

        self._data += data

    def read(self, length):
        data = self._data[self._offset:][:length]
        self._offset += length

        return data

    def pack(self, fmt, *args):
        self.write(struct.pack(self.ENDIANNESS + fmt, *args))

    def unpack(self, fmt):
        data = struct.unpack_from(self.ENDIANNESS + fmt, self._data, self._offset)
        self._offset += struct.calcsize(self.ENDIANNESS + fmt)

        return data

    def clear(self):
        self._data = bytes()
        self._offset = 0

    def pack_sbyte(self, value):
        self.pack('b', int(value))

    def unpack_sbyte(self):
        return self.unpack('b')[0]

    def pack_ubyte(self, value):
        self.pack('B', int(value))

    def unpack_ubyte(self):
        return self.unpack('B')[0]

    def pack_short(self, value):
        self.pack('h', int(value))

    def unpack_short(self):
        return self.unpack('h')[0]

    def pack_ushort(self, value):
        self.pack('H', int(value))

    def unpack_ushort(self):
        return self.unpack('H')[0]

    def pack_string(self, string):
        string = str(string).encode('utf-16be')
        self.pack_ushort(len(string))
        self.write(string)

    def unpack_string(self):
        return self.read(self.unpack_ushort()).decode('utf-16be')

    def pack_bytes(self, byte_array):
        self.pack_ushort(len(byte_array))
        self.write(bytes(byte_array))

    def unpack_bytes(self):
        return bytes(self.read(self.unpack_ushort()))

class PacketError(RuntimeError):
    """
    A packet specific runtime error
    """

class Packet(object):
    """
    A packet object that serialize and deserialize's incoming/outgoing data
    """

    DIRECTION = None
    ID = None

    def __init__(self, handler, dispatcher):
        self._handler = handler
        self._dispatcher = dispatcher

    @property
    def handler(self):
        return self._handler

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def valid(self):
        return self.DIRECTION is not None and self.ID is not None

    @property
    def dispatchable(self):
        return self.deserialize if self.DIRECTION == PacketDirections.DOWNSTREAM else self.serialize

    @property
    def dispatchable_callback(self):
        return self.deserialize_callback if self.DIRECTION == PacketDirections.DOWNSTREAM else self.serialize_callback

    async def handle_send_packet(self, other_data_buffer):
        data_buffer = PacketDataBuffer()
        data_buffer.pack_ushort(self.ID)
        data_buffer.write(other_data_buffer.data)

        other_data_buffer = PacketDataBuffer()
        other_data_buffer.pack_ushort(len(data_buffer.data))
        other_data_buffer.write(data_buffer.data)

        await self._handler.handle_send(self._handler._encryptor.encrypt(other_data_buffer.data))

    async def deserialize(self, *args, **kwargs):
        return None

    async def deserialize_callback(self):
        pass

    async def serialize(self, *args, **kwargs):
        return None

    async def serialize_callback(self):
        pass

class PacketDispatcherError(RuntimeError):
    """
    A packet dispatcher specific runtime error
    """

class PacketDispatcher(object):
    """
    A dispatcher for dispatching Packet objects with incoming/outging data
    """

    def __init__(self, handler):
        self._handler = handler

        # contains a list of packet handler objects that will be dispatched
        # according to their data direction and packet id.
        self._packets = {
            PacketDirections.DOWNSTREAM: {},
            PacketDirections.UPSTREAM: {}
        }

    @property
    def handler(self):
        return self._handler

    @property
    def packets(self):
        return self._packets

    def has_packet(self, packet_direction, packet_id):
        return packet_id in self._packets.get(packet_direction, {})

    def add_packet(self, packet):
        if self.has_packet(packet.DIRECTION, packet.ID):
            return

        self._packets[packet.DIRECTION][packet.ID] = packet(self._handler, self)

    def remove_packet(self, packet):
        if not self.has_packet(packet.DIRECTION, packet.ID):
            return

        del self._packets[packet.DIRECTION][packet.ID]

    def get_packet(self, packet_direction, packet_id):
        if not self.has_packet(packet_direction, packet_id):
            return None

        return self._packets[packet_direction][packet_id]

    async def handle_dispatch_packet(self, packet, *args, **kwargs):
        await self.handle_dispatch(packet.DIRECTION, packet.ID, *args, **kwargs)

    async def handle_dispatch(self, packet_direction, packet_id, *args, **kwargs):
        packet = self.get_packet(packet_direction, packet_id)

        if not packet or not packet.valid:
            return await self.handle_discard_packet(packet_direction, packet_id)

        try:
            data_buffer = await packet.dispatchable(*args, **kwargs)
        except Exception as e:
            raise PacketDispatcherError(e)

        if data_buffer:
            await packet.handle_send_packet(data_buffer)

        try:
            await packet.dispatchable_callback()
        except Exception as e:
            raise PacketDispatcherError(e)

    async def handle_discard_packet(self, packet_direction, packet_id):
        pass
