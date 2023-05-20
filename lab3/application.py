import logging
import time

import controllers.peers_manager as peers_manager
import controllers.pieces_manager as pieces_manager
import models.torrent as torrent
import models.tracker as tracker
from models.block import State
from models.messages import Request


class Application:
    percentage_completed = 0
    last_log_line = ""

    def __init__(self, torrent_file_path: str):
        self.torrent = torrent.Torrent(torrent_file_path)
        self.tracker = tracker.Tracker(self.torrent)

        self.pieces_manager = pieces_manager.PiecesManager(self.torrent)
        self.peers_manager = peers_manager.PeersManager(self.torrent, self.pieces_manager)

        self.sleep_time = 0.1
        
        self.peers_manager.start()

    def start(self) -> None:
        peers_dict = self.tracker.get_peers_from_trackers()
        self.peers_manager.add_peers(peers_dict.values())

        while not self.pieces_manager.all_pieces_completed():
            if not self.peers_manager.has_unchoked_peers():
                time.sleep(1)
                logging.info("No unchocked peers")
                continue

            for piece in self.pieces_manager.pieces:
                index = piece.piece_index

                if self.pieces_manager.pieces[index].is_full:
                    continue

                peer = self.peers_manager.get_random_peer_having_piece(index)
                if not peer:
                    continue

                self.pieces_manager.pieces[index].update_block_status()

                data = self.pieces_manager.pieces[index].get_empty_block()
                if not data:
                    continue

                piece_index, block_offset, block_length = data
                piece_data = Request(piece_index, block_offset, block_length).to_bytes()
                peer.send_to_peer(piece_data)

            self.display_progression()

            time.sleep(self.sleep_time)

        logging.info("File(s) downloaded successfully.")
        self.display_progression()

        self.peers_manager.is_active = False
        exit(0)

    def display_progression(self) -> None:
        new_progression = 0

        for i in range(self.pieces_manager.number_of_pieces):
            for j in range(self.pieces_manager.pieces[i].number_of_blocks):
                if self.pieces_manager.pieces[i].blocks[j].state == State.FULL:
                    new_progression += len(self.pieces_manager.pieces[i].blocks[j].data)

        if new_progression == self.percentage_completed:
            return

        number_of_peers = self.peers_manager.unchoked_peers_count()
        percents = round((new_progression / self.torrent.total_length) * 100, 2)
        complete_num = self.pieces_manager.complete_pieces
        total_num = self.pieces_manager.number_of_pieces
        current_log_line = f"""Connected peers: {number_of_peers} - {percents}%\
                                completed | {complete_num}/{total_num} pieces"""
        
        if current_log_line != self.last_log_line:
            print(current_log_line)

        self.last_log_line = current_log_line
        self.percentage_completed = new_progression
