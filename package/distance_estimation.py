import cv2
import numpy as np


def distance_estimator(image_path,
                       sam_results,
                       depth_anything_model,
                       input_size: int):
    """
    Given:
      - image_path:         path to the RGB image file
      - sam_results:        SAM.predict(...) output, with .masks.data (Tensor[N,H,W])
      - depth_anything_model: an instance of DepthAnythingV2 already .to(DEVICE).eval()
      - input_size:         the int you passed to depth_anything.infer_image

    Returns:
      (farthest_m, closest_m): tuple of floats, meters from camera→wall
    """
    # 1) Load the image and convert to RGB numpy
    frame_bgr = cv2.imread(image_path)
    if frame_bgr is None:
        raise FileNotFoundError(f"Could not read {image_path}")
    frame_rgb = frame_bgr[..., ::-1]

    # 2) Run the depth model
    depth_map = depth_anything_model.infer_image(frame_rgb, input_size)
    # depth_map is a 2D numpy array of floats (meters)

    # 3) Build the boolean wall mask from SAM
    masks = sam_results[0].masks.data.cpu().numpy()  # (N, H, W)
    wall_mask = np.any(masks, axis=0)                # (H, W) bool

    # 4) Extract wall depths and compute extremes
    wall_vals = depth_map[wall_mask]
    if wall_vals.size == 0:
        raise ValueError("No wall pixels detected in the mask.")

    farthest_m = float(wall_vals.max())
    closest_m = float(wall_vals.min())
    return farthest_m, closest_m
