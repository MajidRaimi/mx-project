import cv2
import numpy as np
import itertools
from skimage.graph import route_through_array


def fast_path(mask, start, goal):
    cost = np.where(mask, 1.0, 1e6).astype(float)
    path_rc, _ = route_through_array(
        cost,
        (start[1], start[0]),
        (goal[1], goal[0]),
        fully_connected=True
    )
    return [(c, r) for r, c in path_rc]


def chebyshev(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def held_karp(dist):
    n = len(dist)
    C = {}
    for k in range(1, n):
        C[(1 << k, k)] = (dist[0][k], [0, k])
    for m in range(2, n):
        for subset in itertools.combinations(range(1, n), m):
            bits = sum(1 << bit for bit in subset)
            for k in subset:
                prev = bits ^ (1 << k)
                opts = []
                for j in subset:
                    if j == k:
                        continue
                    cost, path = C[(prev, j)]
                    opts.append((cost + dist[j][k], path + [k]))
                C[(bits, k)] = min(opts, key=lambda x: x[0])
    bits = (1 << n) - 2
    opts = []
    for k in range(1, n):
        cost, path = C[(bits, k)]
        opts.append((cost + dist[k][0], path + [0]))
    return min(opts, key=lambda x: x[0])[1]


def nearest_neighbor_2opt(dist):
    n = len(dist)
    tour = [0]
    unv = set(range(1, n))
    cur = 0
    while unv:
        nxt = min(unv, key=lambda k: dist[cur][k])
        unv.remove(nxt)
        tour.append(nxt)
        cur = nxt
    tour.append(0)

    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                a, b = tour[i - 1], tour[i]
                c, d = tour[j], tour[j + 1]
                old = dist[a][b] + dist[c][d]
                new = dist[a][c] + dist[b][d]
                if new < old:
                    tour[i: j + 1] = reversed(tour[i: j + 1])
                    improved = True
    return tour


def connect_points(grid, results, image_path,
                   gap=50,
                   point_radius=5,
                   line_color=(255, 255, 255),
                   alpha=0.5,
                   risk=1):

    masks = results[0].masks.data.cpu().numpy()
    wall_mask = np.any(masks, axis=0)
    H, W = wall_mask.shape

    ys = list(range(0, H, gap))
    xs = list(range(0, W, gap))
    coords = []
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            if grid[i][j] == 'G' or (risk == 1 and grid[i][j] == 'Y'):
                coords.append((x, y))

    n = len(coords)
    if n < 2:
        return cv2.imread(image_path), []

    dist = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = chebyshev(coords[i], coords[j])
            dist[i][j] = dist[j][i] = d

    if n <= 10:
        tour = held_karp(dist)
    else:
        tour = nearest_neighbor_2opt(dist)

    movement = []
    for u, v in zip(tour, tour[1:]):
        seg = fast_path(wall_mask, coords[u], coords[v])
        if movement:
            movement.pop()
        movement.extend(seg)

    img = cv2.imread(image_path)

    for pt in coords:
        cv2.circle(img, pt, point_radius, (0, 255, 0), -1)

    overlay = img.copy()
    for p0, p1 in zip(movement, movement[1:]):
        cv2.line(overlay, p0, p1, line_color, 2)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

    purple = (255, 0, 255)
    start_pt = coords[tour[0]]
    end_pt = coords[tour[-1]]
    cv2.circle(img, start_pt, point_radius, purple, -1)
    cv2.circle(img, end_pt,   point_radius, purple, -1)

    return img, movement
