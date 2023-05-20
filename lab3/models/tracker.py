import logging
import socket
import struct

import requests
from bcoding import bdecode

import models.peer as peer
from models.torrent import Torrent

from config import MAX_PEERS_CONNECTED, MAX_PEERS_TRY_CONNECT


class SockAddr:
    def __init__(self, 
                 host: str, port: int, 
                 allowed: bool=True):
        self.host: str = host
        self.port: int = port
        self.allowed: bool = allowed

    def __hash__(self) -> str:
        return f"{self.host}:{self.port}"


class Tracker(object):
    def __init__(self, torrent: Torrent):
        self.torrent = torrent
        self.connected_peers = {}
        self.dict_sock_addr = {}
        self.port = 6881
        self.tracker_timeout = 5

    def get_peers_from_trackers(self) -> dict:
        for i, tracker in enumerate(self.torrent.announce_list):
            if len(self.dict_sock_addr) >= MAX_PEERS_TRY_CONNECT:
                break

            tracker_url = tracker[0]

            if not str.startswith(tracker_url, "http"):
                raise Exception("Unsupported protocol")
            
            try:
                self.http_scraper(self.torrent, tracker_url)
            except Exception as e:
                logging.error(f"HTTP scraping failed: {e}")
            else:
                logging.error(f"unknown scheme for: {tracker_url}")

        self.try_peer_connect()

        return self.connected_peers

    def try_peer_connect(self) -> None:
        logging.info(f"Trying to connect to {len(self.dict_sock_addr)} peer(s)")

        for _, sock_addr in self.dict_sock_addr.items():
            if len(self.connected_peers) >= MAX_PEERS_CONNECTED:
                break

            new_peer = peer.Peer(self.torrent.number_of_pieces, 
                                 sock_addr.host, sock_addr.port)
            
            try:
                new_peer.connect()
            except Exception as e:
                print(f"Failed to connect to peer\
                    (ip: {new_peer.host} - port: {new_peer.port} - {e})")
                continue

            print(f'Connected to {len(self.connected_peers)}/{MAX_PEERS_CONNECTED} peers')

            self.connected_peers[new_peer.__hash__()] = new_peer

    def http_scraper(self, torrent: Torrent, tracker_url: str) -> None:
        params = {
            'info_hash': torrent.info_hash,
            'peer_id': torrent.peer_id,
            'uploaded': 0,
            'downloaded': 0,
            'port': self.port,
            'left': torrent.total_length,
            'event': 'started'
        }

        try:
            answer_tracker = requests.get(tracker_url, 
                                          params=params, 
                                          timeout=self.tracker_timeout)
            list_peers = bdecode(answer_tracker.content)
            offset=0
            if not type(list_peers['peers']) == list:
                for _ in range(len(list_peers['peers'])//6):
                    ip = struct.unpack_from("!i", list_peers['peers'], offset)[0]
                    ip = socket.inet_ntoa(struct.pack("!i", ip))
                    offset += 4
                    port = struct.unpack_from("!H",list_peers['peers'], offset)[0]
                    offset += 2
                    s = SockAddr(ip,port)
                    self.dict_sock_addr[s.__hash__()] = s
            else:
                for p in list_peers['peers']:
                    s = SockAddr(p['ip'], p['port'])
                    self.dict_sock_addr[s.__hash__()] = s

        except Exception as e:
            logging.exception(f"HTTP scraping failed: {e}")
