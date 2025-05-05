
import cv2
import numpy as np


def draw_points(results, image_path, gap=50, point_radius=5, thickness=-1):
    masks = results[0].masks.data.cpu().numpy()
    combined_mask = np.any(masks, axis=0)
    H, W = combined_mask.shape

    ys = list(range(0, H, gap))
    xs = list(range(0, W, gap))
    grid = [['' for _ in xs] for _ in ys]

    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            grid[i][j] = 'G' if combined_mask[y, x] else 'R'

    neigh8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
              (0, 1), (1, -1), (1, 0), (1, 1)]
    for i in range(len(ys)):
        for j in range(len(xs)):
            if grid[i][j] == 'G':
                for dy, dx in neigh8:
                    ni, nj = i+dy, j+dx
                    if 0 <= ni < len(ys) and 0 <= nj < len(xs):
                        if grid[ni][nj] == 'R':
                            grid[i][j] = 'Y'
                            break

    last_i, last_j = len(ys)-1, len(xs)-1
    for j in range(len(xs)):
        grid[0][j] = 'R'
        grid[last_i][j] = 'R'
    for i in range(len(ys)):
        grid[i][0] = 'R'
        grid[i][last_j] = 'R'

    img = cv2.imread(image_path)
    color_map = {
        'G': (0, 255,   0),
        'Y': (0, 255, 255),
        'R': (0,   0, 255),
    }
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            col = color_map[grid[i][j]]
            cv2.circle(img, (x, y), point_radius, col, thickness)
    return img, grid