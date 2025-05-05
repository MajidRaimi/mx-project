import numpy as np
import torch
import cv2
from PIL import Image
from transformers.pipelines import pipeline


def pick_wall_point(image: Image.Image, semseg_model: str = "nvidia/segformer-b0-finetuned-ade-512-512"):

    w, h = image.size
    device = 0 if torch.cuda.is_available() else -1
    semseg = pipeline(
        "image-segmentation",
        model=semseg_model,
        device=device,
        reduce_labels=False
    )
    sem = semseg(image)

    wall_mask = np.zeros((h, w), dtype=bool)
    for r in sem:  # type: ignore
        if r["label"].lower() == "wall":  # type: ignore
            mask = np.array(r["mask"].resize((w, h))).astype(  # type: ignore
                bool)  # type: ignore
            wall_mask |= mask

    wall_uint = wall_mask.astype(np.uint8) * 255
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        wall_mask.astype(np.uint8), 8)  # type: ignore

    areas = stats[1:, cv2.CC_STAT_AREA]
    best_label = 1 + int(np.argmax(areas))
    best_centroid = centroids[best_label]

    cx, cy = map(int, best_centroid)
    cx = max(0, min(w-1, cx))
    cy = max(0, min(h-1, cy))
    bw_image = Image.fromarray(wall_uint, mode="L")
    return bw_image, (cx, cy)
