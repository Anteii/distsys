from typing import List, Tuple
from utils import interval_contains
import random


random.seed(42)


class Finger:

    start: int
    interval: Tuple[int, int] 
    node: 'ChordNode'

    def __init__(self, key: int, m: int, i: int, node: 'ChordNode'):
        self.interval = (
            (key + 2 ** i) % 2 ** m,
            (key + 2 ** (i+1)) % 2 ** m
        )
        self.start = self.interval[0]
        self.node = node

    def __repr__(self) -> str:
        start, end = self.interval
        return f"Finger({start}, ({start}:{end}), {self.node.id})"


class ChordNode:

    id: int
    finger: List[Finger]
    successor: 'ChordNode'
    predecessor: 'ChordNode'
    m: int
    
    def __init__(self, key: int, m: int):
        self.m = m
        self.id = key
        self.finger = [Finger(key, m, i, self) for i in range(0, m)]
        self.successor = self.finger[0].node
        self.predecessor = self.finger[0].node

    def get_successor(self) -> 'ChordNode':
        return self.successor

    def set_successor(self, node: 'ChordNode') -> None:
        self.successor = node

    def get_predecessor(self) -> 'ChordNode':
        return self.predecessor

    def set_predecessor(self, node) -> None:
        self.predecessor = node
    
    def find_successor(self, node_id: int) -> 'ChordNode':
        node = self.find_predecessor(node_id)
        return node.get_successor()

    def find_predecessor(self, node_id: int) -> 'ChordNode':
        node = self
        while not interval_contains(self.m, node_id, node.id, 
                                    node.get_successor().id, 2):
            node = node.closest_preceding_finger(node_id)
        return node
    
    def closest_preceding_finger(self, node_id: int) -> 'ChordNode':
        for i in range(self.m-1, -1, -1):
            node = self.finger[i].node
            if interval_contains(self.m, node.id, self.id, node_id, 0):
                return node
        return self
 
    def join(self, node: 'ChordNode') -> None:
        if node:
            self.set_predecessor(None)
            self.set_successor(node.find_successor(self.id))
            self.init_finger_table(node)
            self.update_others()
        else:
            for i in range(self.m):
                self.finger[i].node = self
            self.set_predecessor(self)
            
    def init_finger_table(self, node: 'ChordNode') -> None:
        self.finger[0].node = node.find_successor(self.finger[0].start)

        self.set_predecessor(self.get_successor().get_predecessor())
        self.get_successor().set_predecessor(self)
        
        for i in range(0, self.m-1):
            if interval_contains(self.m, self.finger[i+1].start, self.id, 
                                 self.finger[i].node.id, 1):
                self.finger[i+1].node = self.finger[i].node
            else:
                self.finger[i+1].node = node.find_successor(self.finger[i+1].start)
                
    def update_others(self) -> None:
        for i in range(0, self.m):
            index = (self.id - 2 ** i) % 2 ** self.m
            self.find_predecessor(index).update_finger_table(self, i)
            
    def update_finger_table(self, node: 'ChordNode', ind: int) -> None:
        if interval_contains(self.m, node.id, self.id, self.finger[ind].node.id, 1):
            self.finger[ind].node = node
            self.get_predecessor().update_finger_table(node, ind)
    
    def stabilize(self) -> None:
        x = self.get_successor().get_predecessor()
        if interval_contains(self.m, x.id, self.id, self.get_successor().id, 0):
            self.set_successor(x)
        self.get_successor().notify(self)

    def notify(self, node) -> None:
        predecessor = self.get_predecessor()
        if predecessor is None or\
            interval_contains(self.m, node.id, predecessor.id, self.id, 0):
            self.set_predecessor(node)

    def fix_fingers(self) -> None:
        ind = random.randint(0, self.m-1)
        self.finger[ind].node = self.find_successor(self.finger[ind].start)
        
    def remove(self) -> None:
        if self.get_predecessor():
            self.get_predecessor().set_successor(self.get_successor())
        self.get_successor().set_predecessor(self.get_predecessor())

        for ind in range(self.m):
            j = self.id - 2 ** ind
            self.find_predecessor(j).update_finger_table(self.get_successor(), ind)

    def __repr__(self) -> str:
        string = "#" * 20 + "\n"
        string += f"ChordNode(id{self.id})" + "\n"
        string += "Finger table" + "\n"
        for entry in self.finger:
            string += entry.__repr__() + "\n"
        return string

def stabilisation(nodes: List['ChordNode']) -> None:
    for i in range(2 ** nodes[0].m ** 2 + 1, -1, -1):
        nodes[i % len(nodes)].stabilize()
        nodes[i % len(nodes)].fix_fingers()