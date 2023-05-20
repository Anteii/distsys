import logging
import random
import select
import socket as socklib
from threading import Thread
from typing import List

import models.messages as messages
from models.peer import Peer
from controllers.pieces_manager import PiecesManager
from models.torrent import Torrent
from utils.utils import read_from_socket


class PeersManager(Thread):
    def __init__(self, torrent: Torrent, pieces_manager: PiecesManager):
        super(PeersManager, self).__init__()
        self.peers: List[Peer] = []
        self.torrent = torrent
        self.pieces_manager = pieces_manager
        self.pieces_by_peer = [[0, []] for _ in range(pieces_manager.number_of_pieces)]
        self.is_active = True

    def get_random_peer_having_piece(self, index: int) -> Peer:
        ready_peers = list(filter(lambda peer: peer.is_ready(index), self.peers))
        return random.choice(ready_peers) if ready_peers else None

    def has_unchoked_peers(self) -> bool:
        return any(peer.is_unchoked() for peer in self.peers)

    def unchoked_peers_count(self) -> bool:
        return len([peer for peer in self.peers if peer.is_unchoked()])

    def run(self) -> None:
        while self.is_active:
            sockets = [peer.socket for peer in self.peers]
            read_list, _, _ = select.select(sockets, [], [], 1)

            for socket in read_list:
                peer = self.get_peer_by_socket(socket)
                if not peer.healthy:
                    self.remove_peer(peer)
                    continue
                try:
                    payload = read_from_socket(socket)
                except Exception as e:
                    logging.error(f"Recv failed {e}")
                    self.remove_peer(peer)
                    continue

                peer.read_buffer += payload

                for message in peer.get_messages():
                    self._process_new_message(message, peer)

    def _do_handshake(self, peer: Peer) -> bool:
        try:
            peer.send_to_peer(messages.Handshake(self.torrent.info_hash).to_bytes())
            logging.info(f"New peer added : {peer.host}")
            return True

        except Exception:
            logging.exception(f"Error when sending handshake to peer ({peer.host})")

        return False

    def add_peers(self, peers: List[Peer]) -> None:
        for peer in peers:
            if self._do_handshake(peer):
                self.peers.append(peer)

    def remove_peer(self, peer: Peer) -> None:
        if peer in self.peers:
            try:
                peer.socket.close()
            except Exception:
                logging.exception(f"Error closing connection with peer ({peer.host})")

            self.peers.remove(peer)

    def get_peer_by_socket(self, socket: socklib.socket) -> Peer:
        for peer in self.peers:
            if socket == peer.socket:
                return peer

        raise Exception("Peer is not on the list")

    def _process_new_message(self, new_message: messages.Message, peer: Peer) -> None:
        unaparam_msg = {messages.Choke: peer.handle_choke, 
                        messages.UnChoke: peer.handle_unchoke,
                        messages.Interested: peer.handle_interested, 
                        messages.NotInterested: peer.handle_not_interested,
                        messages.Port: peer.handle_port_request,
                        messages.Cancel: peer.handle_cancel}
        param_msg = {messages.Have: peer.handle_have,
                     messages.BitField: peer.handle_bitfield,
                     messages.Request: peer.handle_request,
                     messages.Piece: peer.handle_piece}
        
        if isinstance(new_message, messages.Handshake)\
            or isinstance(new_message, messages.KeepAlive):
            logging.error("Can't handle Handshake or KeepALlive now")
        elif new_message.__class__ in unaparam_msg:
            unaparam_msg[new_message.__class__]()
        elif new_message.__class__ in param_msg:
            param_msg[new_message.__class__](new_message)
        else:
            logging.error("Unknown message")
