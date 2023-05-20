from typing import Any, Dict, List

import bitstring
from pubsub import pub

from models.piece import Piece


class PiecesManager(object):
    def __init__(self, torrent):
        self.torrent = torrent
        self.number_of_pieces = int(torrent.number_of_pieces)
        self.bitfield = bitstring.BitArray(self.number_of_pieces)
        self.pieces = self._generate_pieces()
        self.files = self._load_files()
        self.complete_pieces = 0

        for file in self.files:
            id_piece = file['idPiece']
            self.pieces[id_piece].files.append(file)

        # Очереди сообщений
        pub.subscribe(self.receive_block_piece, 'PiecesManager.Piece')
        pub.subscribe(self.update_bitfield, 'PiecesManager.PieceCompleted')

    def update_bitfield(self, piece_index: int) -> None:
        self.bitfield[piece_index] = 1

    def receive_block_piece(self, piece: Piece) -> None:
        piece_index, piece_offset, piece_data = piece

        if self.pieces[piece_index].is_full:
            return

        self.pieces[piece_index].set_block(piece_offset, piece_data)

        if self.pieces[piece_index].are_all_blocks_full():
            if self.pieces[piece_index].set_to_full():
                self.complete_pieces +=1


    def get_block(self, 
                  piece_index: int, 
                  block_offset: int,
                  block_length: int) -> bytes:
        
        for piece in self.pieces:
            if piece_index == piece.piece_index:
                if piece.is_full:
                    return piece.get_block(block_offset, block_length)
                else:
                    break

        return None

    def all_pieces_completed(self) -> bool:
        return all(piece.is_full for piece in self.pieces)

    def _generate_pieces(self) -> List[Piece]:
        pieces = []
        piece_num = self.number_of_pieces
        last_piece = piece_num - 1
        torrent_length = self.torrent.total_length
        piece_length = self.torrent.piece_length
        for i in range(piece_num):
            start = i * 20
            end = start + 20

            if i == last_piece:
                last_piece_length = torrent_length  - (piece_num - 1) * piece_length
                pieces.append(Piece(i, last_piece_length, self.torrent.pieces[start:end]))
            else:
                pieces.append(Piece(i, piece_length, self.torrent.pieces[start:end]))

        return pieces

    def _load_files(self) -> Dict[str, Any]:
        files = []
        piece_offset = 0
        piece_size_used = 0

        for f in self.torrent.file_names:
            current_size_file = f["length"]
            file_offset = 0

            while current_size_file > 0:
                id_piece = piece_offset // self.torrent.piece_length
                piece_size = self.pieces[id_piece].piece_size - piece_size_used

                if current_size_file - piece_size < 0:
                    file = {"length": current_size_file,
                            "idPiece": id_piece,
                            "fileOffset": file_offset,
                            "pieceOffset": piece_size_used,
                            "path": f["path"]
                            }
                    piece_offset += current_size_file
                    file_offset += current_size_file
                    piece_size_used += current_size_file
                    current_size_file = 0

                else:
                    current_size_file -= piece_size
                    file = {"length": piece_size,
                            "idPiece": id_piece,
                            "fileOffset": file_offset,
                            "pieceOffset": piece_size_used,
                            "path": f["path"]
                            }
                    piece_offset += piece_size
                    file_offset += piece_size
                    piece_size_used = 0

                files.append(file)
        return files
