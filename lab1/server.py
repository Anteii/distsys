import socket
import numpy as np
from imageProcessor import ImageProcessor
import matplotlib
matplotlib.use('Agg') # WSL 2
import matplotlib.pyplot as plt


class Server:
    def __init__(self, 
                 port: int = 8080, host: str = "127.0.0.1", 
                 block_size: int = 1024) -> None:
        self._port = port
        self._block_size = block_size
        self._host = host
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def recieve_image(self) -> np.ndarray:
        
        try:
            self._socket.bind((self._host, self._port))
            self._socket.listen(1)
        except Exception:
            print("Невозможно открыть сокет")
            return
        
        with self._socket as s:
            conn, _ = s.accept()
            
            # read image meta-data
            h, w, c = [int.from_bytes(conn.recv(4), "little") for i in range(3)]
            data_size = h * w * c
            n = data_size // self._block_size + int(data_size % self._block_size != 0)
            data = b""
            for i in range(n):
                data = data + conn.recv(self._block_size)
            
            image = np.frombuffer(data, dtype=np.uint8).reshape(h, w, c)

            return image
    
    def restore_image(self, img: np.ndarray) -> np.ndarray:
        return ImageProcessor.restore(img)
    

server = Server()
recieved_image = server.recieve_image()
original_image = plt.imread("image.jpg")
restored_image = ImageProcessor.restore_image(recieved_image)


std1 = ImageProcessor.compare_images(recieved_image, original_image)
std2 = ImageProcessor.compare_images(restored_image, original_image)

print(f"std (original, noised) = {std1}")
print(f"std (original, denoised) = {std2}")

plt.imsave("recieved_image.jpg", recieved_image)
plt.imsave("restored_image.jpg", restored_image)
