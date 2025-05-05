import cv2
import numpy as np
from PIL import Image

def draw_result_on_image(image, results, color=(0, 255, 0), alpha=0.5):
    if not isinstance(image, np.ndarray):
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    img = image.copy()
    masks = results[0].masks.data.cpu().numpy()
    combined_mask = np.any(masks, axis=0).astype(np.uint8) * 255
    mask_colored = np.zeros_like(img)
    mask_colored[:, :, 1] = combined_mask
    img = cv2.addWeighted(img, 1 - alpha, mask_colored, alpha, 0)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(img_rgb)