from transformers.pipelines import pipeline
from PIL import Image
import numpy as np


def estimate_wall_distance(image_path, sam_results,
                           depth_model="Intel/zoedepth-nyu"):


    masks = sam_results[0].masks.data.cpu().numpy()
    wall_mask = np.any(masks, axis=0)

    pipe = pipeline("depth-estimation", model=depth_model)
    image = Image.open(image_path).convert("RGB")
    out = pipe(image)

    depth_map = out["predicted_depth"][0].cpu().numpy() # type: ignore

    wall_depths = depth_map[wall_mask]
    if wall_depths.size == 0:
        raise ValueError("No wall pixels detected.")
    mean_distance = float(wall_depths.mean())
    return mean_distance
