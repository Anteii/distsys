from struct import unpack

from utils.exceptions import WrongMessageException

from models.messages import *  # noqa: F403


class MessageDispatcher:

    def __init__(self, payload: bytes):
        self.payload = payload

    def dispatch(self):
        try:
            _, message_id, = unpack(">IB", self.payload[:5])
        except Exception as e:
            raise Exception(f"Error when unpacking message : {e}")

        map_id_to_message = {
            0: Choke,  # noqa: F405
            1: UnChoke,  # noqa: F405
            2: Interested,  # noqa: F405
            3: NotInterested,  # noqa: F405
            4: Have,  # noqa: F405
            5: BitField,  # noqa: F405
            6: Request,  # noqa: F405
            7: Piece,  # noqa: F405
            8: Cancel,  # noqa: F405
            9: Port  # noqa: F405
        }

        if message_id not in list(map_id_to_message.keys()):
            raise WrongMessageException("Wrong message id")

        return map_id_to_message[message_id].from_bytes(self.payload)
