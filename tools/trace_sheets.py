"""Trace building footprints and single trees from the plans in data/map_sheets.json.

Buildings: the grey fills of the 2022 land register plan ("base").
Trees: the small circles the landscape architect drew on the site analysis
sheet ("analysis"), which the land register plan does not have.
Writes data/site_objects.json. Needs numpy, pillow, opencv-python-headless.
"""
import base64, io, json, os
import numpy as np, cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E0, N0 = 2672700, 1209450  # the local origin the sheets' matrices use (see index.html)
sheets = {r['id']: r for r in json.load(open(os.path.join(ROOT, 'data', 'map_sheets.json')))}


def load(sid):
    r = sheets[sid]
    img = np.asarray(Image.open(io.BytesIO(base64.b64decode(r['img'].split(',')[1]))).convert('RGB')).astype(np.int16)
    a, b, c, d, e, f = map(float, r['m'].split(','))
    to_lv95 = lambda px, py: (E0 + a * px + c * py + e, N0 - (b * px + d * py + f))
    return img, to_lv95


def buildings():
    img, T = load('base')
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    m = ((r + g + b) / 3 > 105) & ((r + g + b) / 3 < 195) & (b - r < 40) & (b - r > 5)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cs:
        if cv2.contourArea(c) < 40:  # under about 10 m2
            continue
        p = cv2.approxPolyDP(c, 1.5, True)[:, 0, :]
        ring = [T(float(x), float(y)) for x, y in p]
        area = abs(sum(ring[i][0] * ring[i - 1][1] - ring[i - 1][0] * ring[i][1] for i in range(len(ring)))) / 2
        out.append({'ring': ring, 'area': area})
    return out


# Single trees, placed by hand on the site analysis sheet (pixel x, y), with the
# species the architect wrote beside them. Sizes are typical for the species, not measured.
TREES = [
    (222.5, 212.5, 'Sweet chestnut', 20, 7), (216, 246, 'Lime', 20, 6), (181.5, 264, 'Tulip tree', 22, 6),
    (186.5, 301, 'Catalpa', 10, 4), (212.5, 313.5, 'Privet', 6, 2.5), (259, 316.5, 'Chaste tree', 5, 2.5),
    (280.5, 311, 'Judas tree', 7, 3), (314, 281, 'Birch', 16, 4), (314, 296, 'Maple', 16, 5), (331, 296, 'Birch', 16, 4),
    (76, 337.5, 'Beech', 22, 7), (118.5, 331, 'Magnolia', 8, 4), (203, 356, 'Sweet chestnut', 20, 7),
    (204.5, 382.5, 'Maple', 16, 5), (370, 331, 'Maple', 16, 5), (410, 337.5, 'Oak', 22, 8),
    (438, 576, 'Fruit tree', 6, 3), (483.5, 579, 'Fruit tree', 6, 3), (463.5, 596, 'Fruit tree', 6, 3),
    (515, 607, 'Fruit tree', 6, 3), (540, 625, 'Fruit tree', 6, 3), (527.5, 646.5, 'Fruit tree', 6, 3),
    (550, 666, 'Fruit tree', 6, 3), (587, 643.5, 'Fruit tree', 6, 3), (612, 686.5, 'Fruit tree', 5, 2.5),
    (314, 579, 'Fruit tree', 6, 3), (305, 593.5, 'Fruit tree', 6, 3), (335, 588.5, 'Fruit tree', 6, 3),
    (350, 640, 'Fruit tree', 6, 3), (429.5, 672.5, 'Fruit tree', 6, 3),
    (320, 672.5, 'Robinia', 14, 4), (335, 681, 'Shore tree', 14, 4), (352.5, 685, 'Shore tree', 14, 4),
    (378.5, 690, 'Shore tree', 14, 4), (392.5, 698, 'Shore tree', 14, 4), (406, 706.5, 'Shore tree', 14, 4),
    (418.5, 717, 'Shore tree', 14, 4), (430, 725, 'Shore tree', 14, 4), (720, 795, 'Lime', 18, 6),
]
# Groups of trees drawn as a cloud outline: the mature trees in the neighbouring garden of 287.
GROVES = [
    ('Mature trees, garden of 287 (neighbour)', 18, [(25, 500), (60, 468), (120, 455), (180, 466), (238, 492), (262, 530),
     (230, 560), (170, 556), (120, 542), (60, 548), (22, 532)]),
]


def building_height(area):
    # The plans carry no heights: a rough guide by footprint, to be replaced with measured heights.
    return 14 if area > 450 else 9 if area > 120 else 5


if __name__ == '__main__':
    _, T = load('analysis')
    rows = []
    for k, bd in enumerate(sorted(buildings(), key=lambda b: -b['area'])):
        rows.append({'kind': 'building', 'name': f'Building {k + 1}', 'height_m': building_height(bd['area']), 'radius_m': None,
                     'area_m2': round(bd['area']), 'shape': ' '.join(f'{e:.1f},{n:.1f}' for e, n in bd['ring']),
                     'status': 'Traced; height estimated', 'source': 'Grey fills of the 2022 land register plan'})
    for x, y, sp, h, r in TREES:
        e, n = T(x, y)
        rows.append({'kind': 'tree', 'name': sp, 'height_m': h, 'radius_m': r, 'area_m2': None, 'shape': f'{e:.1f},{n:.1f}',
                     'status': 'Placed by hand; size typical for the species', 'source': 'Landscape architect, Site analysis sheet, 29.7.2026'})
    for name, h, pts in GROVES:
        rows.append({'kind': 'grove', 'name': name, 'height_m': h, 'radius_m': None, 'area_m2': None,
                     'shape': ' '.join('%.1f,%.1f' % T(x, y) for x, y in pts),
                     'status': 'Outline traced by hand; height typical', 'source': 'Landscape architect, Site analysis sheet, 29.7.2026'})
    json.dump(rows, open(os.path.join(ROOT, 'data', 'site_objects.json'), 'w'), indent=1, ensure_ascii=False)
    print(len(rows), 'rows')
