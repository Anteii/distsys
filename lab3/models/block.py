from dataclasses import dataclass
from enum import Enum

from config import BLOCK_SIZE


class State(Enum):
    FREE = 0
    PENDING = 1
    FULL = 2


@dataclass(repr=True)
class Block():
    def __init__(self, state: State = State.FREE, 
                 block_size: int = BLOCK_SIZE, 
                 data: bytes = b'', 
                 last_seen: float = 0):
        self.state: State = state
        self.block_size: int = block_size
        self.data: bytes = data
        self.last_seen: float = last_seen
