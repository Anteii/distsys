import hashlib
import logging
import math
import time
from typing import Tuple

from pubsub import pub

from models.block import Block, State
from config import BLOCK_SIZE
from utils.utils import write_piece


class Piece(object):
    def __init__(self, piece_index: int, piece_size: int, piece_hash: str):
        self.piece_index: int = piece_index
        self.piece_size: int = piece_size
        self.piece_hash: str = piece_hash
        self.is_full: bool = False
        self.files = []
        self.raw_data: bytes = b''
        self.number_of_blocks: int = math.ceil(float(piece_size) // BLOCK_SIZE)
        self.blocks: list[Block] = []
        self.free_block_time = 5
        self._init_blocks()

    def update_block_status(self) -> None:
        for i, block in enumerate(self.blocks):
            if block.state == State.PENDING\
                and (time.time() - block.last_seen) > self.free_block_time:
                self.blocks[i] = Block()

    def set_block(self, offset: int, data: bytes) -> None:
        index = int(offset / BLOCK_SIZE)

        if not self.is_full and not self.blocks[index].state == State.FULL:
            self.blocks[index].data = data
            self.blocks[index].state = State.FULL

    def get_block(self, block_offset: int, block_length: int) -> bytes:
        return self.raw_data[block_offset:block_length]

    def get_empty_block(self) -> Tuple[int, int, int]:
        if self.is_full:
            return None

        for block_index, block in enumerate(self.blocks):
            if block.state == State.FREE:
                self.blocks[block_index].state = State.PENDING
                self.blocks[block_index].last_seen = time.time()
                return self.piece_index, block_index * BLOCK_SIZE, block.block_size

        return None

    def are_all_blocks_full(self) -> bool:
        def criteria(b: Block) -> bool:
            return b.state == State.FREE or b.state == State.PENDING
        return not any(criteria(block) for block in self.blocks)

    def set_to_full(self) -> bool:
        data = self._merge_blocks()

        if not self._valid_blocks(data):
            self._init_blocks()
            return False

        self.is_full = True
        self.raw_data = data
        
        write_piece(self)
        pub.sendMessage('PiecesManager.PieceCompleted', piece_index=self.piece_index)

        return True

    def _init_blocks(self) -> None:
        self.blocks = []

        if self.number_of_blocks > 1:
            for i in range(self.number_of_blocks):
                self.blocks.append(Block())

            if (self.piece_size % BLOCK_SIZE) > 0:
                block_size = self.piece_size % BLOCK_SIZE
                self.blocks[self.number_of_blocks - 1].block_size = block_size

        else:
            self.blocks.append(Block(block_size=int(self.piece_size)))
    
    def _merge_blocks(self) -> bytes:
        return b"".join(block.data for block in self.blocks)

    def _valid_blocks(self, piece_raw_data):
        hashed_piece_raw_data = hashlib.sha1(piece_raw_data).digest()

        if hashed_piece_raw_data == self.piece_hash:
            return True

        logging.warning("Error Piece Hash")
        logging.debug(f"{hashed_piece_raw_data} : {self.piece_hash}")
        return False
