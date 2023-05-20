import hashlib
import logging
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from bcoding import bencode

from utils.utils import read_bencode_file


class Torrent(object):
    def __init__(self, torrent_file_path: str):
        self.torrent_file_path: str = torrent_file_path
        self.torrent_file: Dict[str, Any] = {}
        self.total_length: int = 0
        self.piece_length: int = 0
        self.pieces: int = 0
        self.info_hash: bytes = None
        self.peer_id: str = ''
        self.announce_list: List[str] = []
        self.file_names: List[str] = []
        self.number_of_pieces: int = 0
        
        self.load_from_path()

    def load_from_path(self) -> None:
        self.torrent_file = read_bencode_file(self.torrent_file_path)
        self.piece_length = self.torrent_file['info']['piece length']
        self.pieces = self.torrent_file['info']['pieces']
        raw_info_hash = bencode(self.torrent_file['info'])
        self.info_hash = hashlib.sha1(raw_info_hash).digest()
        self.peer_id = self.generate_peer_id()
        self.announce_list = self.get_trakers()
        self.init_files()
        self.number_of_pieces = math.ceil(self.total_length / self.piece_length)
        logging.debug(self.announce_list)
        logging.debug(self.file_names)

        assert(self.total_length > 0)
        assert(len(self.file_names) > 0)

    def init_files(self) -> None:
        root = self.torrent_file['info']['name']
        root_path = Path(root)
        if 'files' in self.torrent_file['info']:
            
            if not root_path.exists():
                os.mkdir(root, 0o777)

            for file in self.torrent_file['info']['files']:
                path_file = Path(root_path, *file["path"])

                if not os.path.exists(os.path.dirname(path_file)):
                    os.makedirs(os.path.dirname(path_file))

                self.file_names.append({"path": path_file , "length": file["length"]})
                self.total_length += file["length"]

        else:
            self.file_names.append({"path": root_path , 
                                    "length": self.torrent_file['info']['length']})
            self.total_length = self.torrent_file['info']['length']

    def get_trakers(self) -> List[str]:
        if 'announce-list' in self.torrent_file:
            return self.torrent_file['announce-list']
        else:
            return [[self.torrent_file['announce']]]

    def generate_peer_id(self) -> bytes:
        return hashlib.sha1(str(time.time()).encode('utf-8')).digest()
