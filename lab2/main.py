from chord import ChordNode, stabilisation
from typing import List

MAX_BITS = 3
    
if __name__ == "__main__":
    nodes: List[ChordNode] = []
    
    prev_node = None
    for ind in [0, 1, 3, 6]:
        chord_node = ChordNode(ind, MAX_BITS)
        nodes.append(chord_node)
        chord_node.join(prev_node)
        prev_node = chord_node
    
        stabilisation(nodes)

    for node in nodes:
        print(node)
        
    removed_node = nodes[-1]
    nodes.remove(removed_node)
    removed_node.remove()
    stabilisation(nodes)
    
    for node in nodes:
        print(node)