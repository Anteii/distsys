import logging
import socket
import struct
import time

import bitstring
from pubsub import pub

import models.messages as messages
from controllers.message_dispatcher import MessageDispatcher


class Peer(object):
    def __init__(self, number_of_pieces: int, 
                 host: str, port:int=6881):
        self.last_call = 0.0
        self.msg_eligibility_threshold = 0.2
        self.has_handshaked = False
        self.healthy = False
        self.read_buffer = b''
        self.socket = None
        self.host = host
        self.port = port
        self.number_of_pieces = number_of_pieces
        self.bit_field = bitstring.BitArray(number_of_pieces)
        self.state = {
            'am_choking': True,
            'am_interested': False,
            'peer_choking': True,
            'peer_interested': False,
        }

    def __hash__(self) -> str:
        return f"{self.host}:{self.port}"

    def connect(self) -> None:
        
        self.socket = socket.create_connection((self.host, self.port), timeout=2)
        self.socket.setblocking(False)
        self.healthy = True
        
        logging.debug(f"Connected to peer ip: {self.host} - port: {self.port}")

    def send_to_peer(self, msg: bytes) -> bool:
        try:
            self.socket.send(msg)
            self.last_call = time.time()
        except Exception as e:
            self.healthy = False
            logging.error(f"Failed to send to peer : {e}")
            return False

        return True

    def is_ready(self, index: int) -> bool:
        return self.is_eligible() and self.is_unchoked()\
                and self.am_interested() and self.has_piece(index)
    
    def is_eligible(self) -> bool:
        now = time.time()
        return (now - self.last_call) > self.msg_eligibility_threshold

    def has_piece(self, index: int) -> bool:
        return self.bit_field[index]

    def am_choking(self) -> bool:
        return self.state['am_choking']

    def is_choking(self) -> bool:
        return self.state['peer_choking']

    def is_unchoked(self) -> bool:
        return not self.is_choking()

    def is_interested(self) -> bool:
        return self.state['peer_interested']

    def am_interested(self) -> bool:
        return self.state['am_interested']

    def handle_choke(self) -> None:
        logging.debug(f'Handle_choke - {self.host}')
        self.state['peer_choking'] = True

    def handle_unchoke(self) -> None:
        logging.debug(f'Handle_unchoke - {self.host}')
        self.state['peer_choking'] = False

    def handle_interested(self) -> None:
        logging.debug(f'Handle_interested - {self.host}')
        self.state['peer_interested'] = True

        if self.am_choking():
            unchoke = messages.UnChoke().to_bytes()
            self.send_to_peer(unchoke)

    def handle_not_interested(self) -> None:
        logging.debug(f'Handle_not_interested - {self.host}')
        self.state['peer_interested'] = False

    def handle_have(self, have: messages.Have)-> None:
        logging.debug(f'Handle_have - ip: {self.host} - piece: {have.piece_index}')
        self.bit_field[have.piece_index] = True

        if self.is_choking() and not self.state['am_interested']:
            self.send_to_peer(messages.Interested().to_bytes())
            self.state['am_interested'] = True

    def handle_bitfield(self, bitfield: messages.BitField) -> None:
        logging.debug(f'Handle_bitfield - {self.host} - {bitfield.bitfield}')
        self.bit_field = bitfield.bitfield

        if self.is_choking() and not self.state['am_interested']:
            self.send_to_peer(messages.Interested().to_bytes())
            self.state['am_interested'] = True

    def handle_request(self, request: messages.Request) -> None:
        logging.debug(f'Handle_request - {self.host}')
        if self.is_interested() and self.is_unchoked():
            pub.sendMessage('PiecesManager.PeerRequestsPiece', 
                            request=request, peer=self)

    def handle_piece(self, message: messages.Piece) -> None:
        pub.sendMessage('PiecesManager.Piece', piece=(message.piece_index, 
                                                      message.block_offset, 
                                                      message.block))

    def handle_cancel(self) -> None:
        logging.debug(f'Handle_cancel - {self.host}')

    def handle_port_request(self) -> None:
        logging.debug('Handle_port_request - {self.host}')

    def _handle_handshake(self) -> bool:
        try:
            handshake_message = messages.Handshake.from_bytes(self.read_buffer)
            self.has_handshaked = True
            self.read_buffer = self.read_buffer[handshake_message.total_length:]
            logging.debug(f'Handle_handshake - {self.host}')
            return True

        except Exception:
            logging.exception("First message should always be a handshake message")
            self.healthy = False

        return False

    def _handle_keep_alive(self) -> bool:
        try:
            keep_alive = messages.KeepAlive.from_bytes(self.read_buffer)
            logging.debug(f'handle_keep_alive - {self.host}')
        except messages.WrongMessageException:
            return False
        except Exception:
            buff_len = len(self.read_buffer)
            logging.exception(f"Error KeepALive, (need at least 4 bytes : {buff_len})")
            return False

        self.read_buffer = self.read_buffer[keep_alive.total_length:]
        return True

    def get_messages(self) -> messages.Message:
        while len(self.read_buffer) > 4 and self.healthy:
            if (not self.has_handshaked and self._handle_handshake())\
                or self._handle_keep_alive():
                continue

            payload_length, = struct.unpack(">I", self.read_buffer[:4])
            total_length = payload_length + 4

            if len(self.read_buffer) < total_length:
                break
            else:
                payload = self.read_buffer[:total_length]
                self.read_buffer = self.read_buffer[total_length:]
            try:
                received_message = MessageDispatcher(payload).dispatch()
                yield received_message
            except Exception as e:
                logging.exception(e)
