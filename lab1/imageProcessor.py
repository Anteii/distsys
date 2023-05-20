from abc import ABCMeta
import numpy as np
from cv2 import medianBlur

np.random.seed(42)

class ImageProcessor(ABCMeta):
    @staticmethod
    def induce_noise(image: np.ndarray, p: int = 0.2) -> np.ndarray:
        mask = np.random.uniform(low=0, high=1, size=image.shape)
        noise = np.random.uniform(low=0, high=255, size=image.shape).astype(np.uint8)
        
        return np.where(mask > p, image, noise)
    
    @staticmethod
    def restore_image(image: np.ndarray, ksize: int = 5) -> np.ndarray:
        return medianBlur(image, ksize=ksize)

    @staticmethod
    def compare_images(image1: np.ndarray, image2: np.ndarray) -> float:
        h, w, c = image1.shape
        return np.sqrt(np.sum((image1-image2)**2)/(h * w * c))