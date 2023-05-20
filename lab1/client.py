import socket
import numpy as np
from imageProcessor import ImageProcessor
import matplotlib
matplotlib.use('Agg') # WSL 2
import matplotlib.pyplot as plt


class Client:
    def __init__(self, 
                 port: int = 8080, host: str = "127.0.0.1", 
                 block_size: int = 1024) -> None:
        self._port = port
        self._block_size = block_size
        self._host = host
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def send_image(self, image: np.ndarray) -> None:
        image_with_error = self._induce_error(image)
        binary_data = image_with_error.tobytes()
        data_size = len(binary_data)
        
        with self._socket as s:
            try:
                s.connect((self._host, self._port))
            except Exception:
                print("Невозможно подключиться к серверу")
                return
            
            try:
                meta_data = b"".join(
                    [i.to_bytes(4, "little") for i in image_with_error.shape]
                )
                s.sendall(meta_data)
            except Exception:
                print("Ошибка при отправке метаданных")
                return
               
            try:
                sent_size = 0
                while sent_size < data_size:
                    s.sendall(binary_data[sent_size:sent_size+self._block_size])
                    sent_size = min(data_size, sent_size + self._block_size)
            except Exception:
                block_ind = sent_size // self._block_size
                print(f"Ошибка при отправке изображения в блоке: {block_ind}")
                return
            
    def _induce_error(self, image: np.ndarray) -> np.ndarray:
        noised_image = ImageProcessor.induce_noise(image)
        return noised_image
        

client = Client()
image = plt.imread("image.jpg")
client.send_image(image)
