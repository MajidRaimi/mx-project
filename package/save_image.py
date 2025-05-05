import cv2
import numpy as np

def save_image(image, path):
    if not isinstance(image, np.ndarray):
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    cv2.imwrite(path, image)

def save_image_with_point(image, pt, path, color=(0, 0, 255), radius=5, thickness=-1):
    if not isinstance(image, np.ndarray):
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    img_copy = image.copy()
    cv2.circle(img_copy, pt, radius, color, thickness)
    cv2.imwrite(path, img_copy)
