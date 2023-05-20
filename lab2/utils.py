def interval_contains(m: int, node_id: int, 
                   start: int, end: int, 
                   border_type: int):
    
    end += 2 ** m if start >= end else 0
    node_id += 2 ** m if start > node_id else 0

    flag = start < node_id < end
    if border_type == 1:
        flag = flag or start == node_id
    elif border_type == 2:
        flag = flag or end == node_id
    
    return flag
    