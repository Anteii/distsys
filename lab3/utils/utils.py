import errno
import logging
import socket
from pathlib import Path
from typing import Any, Dict

from bcoding import bdecode


def read_bencode_file(path: str) -> Dict[str, Any]:
    with open(path, 'rb') as file:
            return bdecode(file)
        
        
def read_from_socket(sock: socket.socket, buff_size: int=4096) -> bytes:
    data = b''
    
    while True:
        try:
            buff = sock.recv(buff_size)
            if len(buff) == 0:
                break

            data += buff
        except socket.error as e:
            err = e.args[0]
            if err != errno.EAGAIN or err != errno.EWOULDBLOCK:
                logging.debug("Wrong errno {}".format(err))
            break
        except Exception:
            logging.exception("Recv failed")
            break

    return data

# couldn't solve circular dependecy
def write_piece(piece) -> None:
    for file in piece.files:
        path = Path(file["path"])
        file_offset = file["fileOffset"]
        piece_offset = file["pieceOffset"]
        length = file["length"]

        try:
            with open(path, 'r+b' if path.exists() else "wb") as f:
                f.seek(file_offset)
                f.write(piece.raw_data[piece_offset:piece_offset + length])
                f.close()
        except Exception:
            logging.exception("Can't write to file")

        