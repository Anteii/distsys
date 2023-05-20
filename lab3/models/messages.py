from abc import ABC, abstractmethod
from struct import pack, unpack

import bitstring

from utils.exceptions import WrongMessageException

HANDSHAKE_PSTR_V1 = b"BitTorrent protocol"
HANDSHAKE_PSTR_LEN = len(HANDSHAKE_PSTR_V1)
LENGTH_PREFIX = 4


class Message(ABC):

    @abstractmethod
    def to_bytes(self) -> bytes:
        ...

    @abstractmethod
    def from_bytes(cls, payload: bytes) -> 'Message':
        ...


def assert_cmp_msg_types(msg_id1: int, msg_id2: int, msg_type: str) -> None:
    if msg_id1 != msg_id2:
        raise WrongMessageException(f"Not a {msg_type} message")


class Handshake(Message):
    """
        Handshake = <pstrlen><pstr><reserved><info_hash><peer_id>
            - pstrlen = length of pstr (1 byte)
            - pstr = string identifier of the protocol: "BitTorrent protocol" (19 bytes)
            - reserved = 8 reserved bytes indicating extensions to the protocol (8 bytes)
            - info_hash = hash of the value of the 'info' key of the torrent file (20 bytes)
            - peer_id = unique identifier of the Peer (20 bytes)

        Total length = payload length = 49 + len(pstr) = 68 bytes (for BitTorrent v1)
    """
    payload_length = 68
    total_length = payload_length

    def __init__(self, info_hash: bytes, peer_id: bytes=b'-ZZ0007-000000000000'):
        self.peer_id = peer_id
        self.info_hash = info_hash

    def to_bytes(self) -> bytes:
        reserved = b'\x00' * 8
        handshake = pack(f">B{HANDSHAKE_PSTR_LEN}s8s20s20s",
                         HANDSHAKE_PSTR_LEN,
                         HANDSHAKE_PSTR_V1,
                         reserved,
                         self.info_hash,
                         self.peer_id)

        return handshake

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'Handshake':
        pstrlen, = unpack(">B", payload[:1])
        pstr, _, info_hash, peer_id = unpack(f">{pstrlen}s8s20s20s", 
                                             payload[1:cls.total_length])

        if pstr != HANDSHAKE_PSTR_V1:
            raise ValueError("Invalid string identifier of the protocol")

        return Handshake(info_hash, peer_id)


class KeepAlive(Message):
    """
        KEEP_ALIVE = <length>
            - payload length = 0 (4 bytes)
    """
    payload_length = 0
    total_length = 4

    def to_bytes(self) -> bytes:
        return pack(">I", self.payload_length)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'KeepAlive':
        payload_length = unpack(">I", payload[:cls.total_length])

        if payload_length != 0:
            raise WrongMessageException("Not a Keep Alive message")

        return KeepAlive()


class Choke(Message):
    """
        CHOKE = <length><message_id>
            - payload length = 1 (4 bytes)
            - message id = 0 (1 byte)
    """
    message_id = 0
    chokes_me = True

    payload_length = 1
    total_length = 5

    def to_bytes(self) -> bytes:
        return pack(">IB", self.payload_length, self.message_id)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'Choke':
        _, message_id = unpack(">IB", payload[:cls.total_length])
        
        assert_cmp_msg_types(message_id, cls.message_id, "Choke")

        return Choke()


class UnChoke(Message):
    """
        UnChoke = <length><message_id>
            - payload length = 1 (4 bytes)
            - message id = 1 (1 byte)
    """
    message_id = 1
    chokes_me = False

    payload_length = 1
    total_length = 5

    def to_bytes(self) -> bytes:
        return pack(">IB", self.payload_length, self.message_id)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'UnChoke':
        _, message_id = unpack(">IB", payload[:cls.total_length])

        assert_cmp_msg_types(message_id, cls.message_id, "Unchoke")

        return UnChoke()


class Interested(Message):
    """
        INTERESTED = <length><message_id>
            - payload length = 1 (4 bytes)
            - message id = 2 (1 byte)
    """
    message_id = 2
    interested = True

    payload_length = 1
    total_length = payload_length + 4

    def to_bytes(self) -> bytes:
        return pack(">IB", self.payload_length, self.message_id)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'Interested':
        _, message_id = unpack(">IB", payload[:cls.total_length])

        assert_cmp_msg_types(message_id, cls.message_id, "Interested")

        return Interested()


class NotInterested(Message):
    """
        NOT INTERESTED = <length><message_id>
            - payload length = 1 (4 bytes)
            - message id = 3 (1 byte)
    """
    message_id = 3
    interested = False

    payload_length = 1
    total_length = 5

    def to_bytes(self) -> bytes:
        return pack(">IB", self.payload_length, self.message_id)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'NotInterested':
        _, message_id = unpack(">IB", payload[:cls.total_length])
        
        assert_cmp_msg_types(message_id, cls.message_id, "NotInterested")

        return Interested()


class Have(Message):
    """
        HAVE = <length><message_id><piece_index>
            - payload length = 5 (4 bytes)
            - message_id = 4 (1 byte)
            - piece_index = zero based index of the piece (4 bytes)
    """
    message_id = 4

    payload_length = 5
    total_length = payload_length + 4

    def __init__(self, piece_index):
        self.piece_index = piece_index

    def to_bytes(self) -> bytes:
        pack(">IBI", self.payload_length, self.message_id, self.piece_index)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'Have':
        __package__, message_id, piece_index = unpack(">IBI", payload[:cls.total_length])
        
        assert_cmp_msg_types(message_id, cls.message_id, "Have")

        return Have(piece_index)


class BitField(Message):
    """
        BITFIELD = <length><message id><bitfield>
            - payload length = 1 + bitfield_size (4 bytes)
            - message id = 5 (1 byte)
            - bitfield = bitfield representing downloaded pieces (bitfield_size bytes)
    """
    message_id = 5

    # Unknown until given a bitfield
    payload_length = None
    total_length = None

    def __init__(self, bitfield):  # bitfield is a bitstring.BitArray
        self.bitfield = bitfield
        self.bitfield_as_bytes = bitfield.tobytes()
        self.bitfield_length = len(self.bitfield_as_bytes)

        self.payload_length = 1 + self.bitfield_length
        self.total_length = 4 + self.payload_length

    def to_bytes(self) -> bytes:
        return pack(f">IB{self.bitfield_length}s",
                    self.payload_length,
                    self.message_id,
                    self.bitfield_as_bytes)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'BitField':
        payload_length, message_id = unpack(">IB", payload[:5])
        bitfield_length = payload_length - 1

        assert_cmp_msg_types(message_id, cls.message_id, "BitField")

        raw_bitfield, = unpack(f">{bitfield_length}s", 
                               payload[5:5 + bitfield_length])
        
        return BitField(bitstring.BitArray(bytes=bytes(raw_bitfield)))


class Request(Message):
    """
        REQUEST = <length><message id><piece index><block offset><block length>
            - payload length = 13 (4 bytes)
            - message id = 6 (1 byte)
            - piece index = zero based piece index (4 bytes)
            - block offset = zero based of the requested block (4 bytes)
            - block length = length of the requested block (4 bytes)
    """
    message_id = 6

    payload_length = 13
    total_length = payload_length + 4

    def __init__(self, piece_index, block_offset, block_length):
        self.piece_index = piece_index
        self.block_offset = block_offset
        self.block_length = block_length

    def to_bytes(self) -> bytes:
        return pack(">IBIII",
                    self.payload_length,
                    self.message_id,
                    self.piece_index,
                    self.block_offset,
                    self.block_length)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'Request':
        _, message_id, piece_index, block_offset, block_length = unpack(">IBIII",
                                                                        payload[:cls.total_length])
        
        assert_cmp_msg_types(message_id, cls.message_id, "Request")

        return Request(piece_index, block_offset, block_length)


class Piece(Message):
    """
        PIECE = <length><message id><piece index><block offset><block>
        - length = 9 + block length (4 bytes)
        - message id = 7 (1 byte)
        - piece index =  zero based piece index (4 bytes)
        - block offset = zero based of the requested block (4 bytes)
        - block = block as a bytestring or bytearray (block_length bytes)
    """
    message_id = 7

    payload_length = None
    total_length = None

    def __init__(self, block_length, piece_index, block_offset, block):
        self.block_length = block_length
        self.piece_index = piece_index
        self.block_offset = block_offset
        self.block = block

        self.payload_length = 9 + block_length
        self.total_length = 4 + self.payload_length

    def to_bytes(self) -> bytes:
        return pack(f">IBII{self.block_length}s",
                    self.payload_length,
                    self.message_id,
                    self.piece_index,
                    self.block_offset,
                    self.block)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'Piece':
        block_length = len(payload) - 13
        _, message_id, piece_index, block_offset, block = unpack(f">IBII{block_length}s",
                                                                 payload[:13 + block_length])

        assert_cmp_msg_types(message_id, cls.message_id, "Piece")

        return Piece(block_length, piece_index, block_offset, block)


class Cancel(Message):
    """CANCEL = <length><message id><piece index><block offset><block length>
        - length = 13 (4 bytes)
        - message id = 8 (1 byte)
        - piece index = zero based piece index (4 bytes)
        - block offset = zero based of the requested block (4 bytes)
        - block length = length of the requested block (4 bytes)"""
    message_id = 8

    payload_length = 13
    total_length = payload_length + 4

    def __init__(self, piece_index, block_offset, block_length):
        self.piece_index = piece_index
        self.block_offset = block_offset
        self.block_length = block_length

    def to_bytes(self) -> bytes:
        return pack(">IBIII",
                    self.payload_length,
                    self.message_id,
                    self.piece_index,
                    self.block_offset,
                    self.block_length)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'Cancel':
        _, message_id, piece_index, block_offset, block_length = unpack(">IBIII",
                                                                        payload[:cls.total_length])
        
        assert_cmp_msg_types(message_id, cls.message_id, "Cancel")

        return Cancel(piece_index, block_offset, block_length)


class Port(Message):
    """
        PORT = <length><message id><port number>
            - length = 5 (4 bytes)
            - message id = 9 (1 byte)
            - port number = listen_port (4 bytes)
    """
    message_id = 9

    payload_length = 5
    total_length = payload_length + 4

    def __init__(self, listen_port):
        self.listen_port = listen_port

    def to_bytes(self) -> bytes:
        return pack(">IBI",
                    self.payload_length,
                    self.message_id,
                    self.listen_port)

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'Port':
        _, message_id, listen_port = unpack(">IBI", payload[:cls.total_length])

        assert_cmp_msg_types(message_id, cls.message_id, "Port")

        return Port(listen_port)
