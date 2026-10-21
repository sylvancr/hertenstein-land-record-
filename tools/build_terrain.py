"""Build data/terrain.json for terrain.html.

Reads AWS Terrain Tiles (Terrarium encoding, public, no key) around the land,
resamples them onto a 6 m LV95 grid, and precomputes what the page cannot
cheaply work out in the browser: the skyline seen from every cell (48
directions, out to 20 km so the Bürgenstock, Pilatus and Rigi count),
slope, aspect, a wetness index and a hollow/ridge index.

Usage: python3 tools/build_terrain.py <tile-cache-dir>
Needs numpy, pillow, pyproj. Tiles are fetched into the cache if missing.
"""
import base64, json, math, os, sys, urllib.request
import numpy as np
from PIL import Image
from pyproj import Transformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '.tiles')
URL = 'https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{x}/{y}.png'

# Grid over the land and its neighbours, LV95, cell centres.
E0, N0, D, NX, NY = 2672640.0, 1209500.0, 6.0, 118, 110
# Terrain Tiles heights sit about 3.4 m below Swiss LN02 here: the lake reads
# 430.2 m (mean level 433.6 m) and the house 454.5 m (swisstopo 457.7 m).
DATUM = 3.4
LAKE = 433.6
N_AZ = 48
FAR = 20000.0

to_wgs = Transformer.from_crs(2056, 4326, always_xy=True)


def tile(z, x, y):
    p = os.path.join(CACHE, f't{z}_{x}_{y}.png')
    if not os.path.exists(p):
        os.makedirs(CACHE, exist_ok=True)
        urllib.request.urlretrieve(URL.format(z=z, x=x, y=y), p)
    a = np.asarray(Image.open(p).convert('RGB')).astype(np.float64)
    return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768


def sampler(z, xs, ys):
    M = np.vstack([np.hstack([tile(z, x, y) for x in xs]) for y in ys])
    n = 2 ** z

    def f(E, N):
        lon, lat = to_wgs.transform(np.asarray(E), np.asarray(N))
        px = ((lon + 180) / 360 * n - xs[0]) * 256 - 0.5
        py = ((1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n - ys[0]) * 256 - 0.5
        x0 = np.clip(np.floor(px).astype(int), 0, M.shape[1] - 2)
        y0 = np.clip(np.floor(py).astype(int), 0, M.shape[0] - 2)
        fx, fy = np.clip(px - x0, 0, 1), np.clip(py - y0, 0, 1)
        return (M[y0, x0] * (1 - fx) * (1 - fy) + M[y0, x0 + 1] * fx * (1 - fy)
                + M[y0 + 1, x0] * (1 - fx) * fy + M[y0 + 1, x0 + 1] * fx * fy) + DATUM
    return f


def grid_sample(f, e0, n0, d, nx, ny):
    E, N = np.meshgrid(e0 + np.arange(nx) * d, n0 - np.arange(ny) * d)
    return f(E, N)


def bilinear(G, e0, n0, d, E, N):
    px, py = (E - e0) / d, (n0 - N) / d
    x0 = np.clip(np.floor(px).astype(int), 0, G.shape[1] - 2)
    y0 = np.clip(np.floor(py).astype(int), 0, G.shape[0] - 2)
    fx, fy = np.clip(px - x0, 0, 1), np.clip(py - y0, 0, 1)
    return (G[y0, x0] * (1 - fx) * (1 - fy) + G[y0, x0 + 1] * fx * (1 - fy)
            + G[y0 + 1, x0] * (1 - fx) * fy + G[y0 + 1, x0 + 1] * fx * fy)


def smooth(A, passes=1):
    for _ in range(passes):
        P = np.pad(A, 1, mode='edge')
        A = (P[:-2, :-2] + 2 * P[:-2, 1:-1] + P[:-2, 2:] + 2 * P[1:-1, :-2] + 4 * P[1:-1, 1:-1]
             + 2 * P[1:-1, 2:] + P[2:, :-2] + 2 * P[2:, 1:-1] + P[2:, 2:]) / 16
    return A


def in_poly(E, N, ring):
    inside = np.zeros(E.shape, bool)
    xs, ys = ring[:, 0], ring[:, 1]
    j = len(ring) - 1
    for i in range(len(ring)):
        c = ((ys[i] > N) != (ys[j] > N)) & (E < (xs[j] - xs[i]) * (N - ys[i]) / (ys[j] - ys[i] + 1e-12) + xs[i])
        inside ^= c
        j = i
    return inside


def priority_fill(Z, outlet):
    """Fill pits so every cell drains to an outlet (lake or grid edge)."""
    import heapq
    ny, nx = Z.shape
    F = Z.copy()
    done = np.zeros(Z.shape, bool)
    h = []
    for y in range(ny):
        for x in range(nx):
            if outlet[y, x] or y in (0, ny - 1) or x in (0, nx - 1):
                heapq.heappush(h, (F[y, x], y, x))
                done[y, x] = True
    while h:
        z, y, x = heapq.heappop(h)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                yy, xx = y + dy, x + dx
                if 0 <= yy < ny and 0 <= xx < nx and not done[yy, xx]:
                    done[yy, xx] = True
                    F[yy, xx] = max(F[yy, xx], z + 1e-3)
                    heapq.heappush(h, (F[yy, xx], yy, xx))
    return F


def flow_accumulation(F, outlet):
    """Multiple-flow-direction (Freeman, p=1.1) contributing area in m2."""
    ny, nx = F.shape
    A = np.full(F.shape, D * D)
    order = np.argsort(-F, axis=None)
    nb = [(dy, dx, math.hypot(dy, dx)) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
    for k in order:
        y, x = divmod(int(k), nx)
        if outlet[y, x]:
            continue
        w = []
        for dy, dx, L in nb:
            yy, xx = y + dy, x + dx
            if 0 <= yy < ny and 0 <= xx < nx:
                s = (F[y, x] - F[yy, xx]) / (L * D)
                if s > 0:
                    w.append((yy, xx, s ** 1.1 * (0.5 if L > 1 else 1)))
        t = sum(v for _, _, v in w)
        for yy, xx, v in w:
            A[yy, xx] += A[y, x] * v / t
    return A


def b64(arr):
    return base64.b64encode(np.ascontiguousarray(arr).tobytes()).decode()


def main():
    fine = sampler(15, list(range(17146, 17151)), list(range(11519, 11524)))
    coarse = sampler(12, list(range(2140, 2148)), list(range(1437, 1445)))

    Z = smooth(grid_sample(fine, E0, N0, D, NX, NY), 2)
    E, N = np.meshgrid(E0 + np.arange(NX) * D, N0 - np.arange(NY) * D)

    parcels = json.load(open(os.path.join(ROOT, 'data', 'parcels.json')))
    onland = np.zeros(Z.shape, bool)
    for p in parcels:
        ring = np.array([[float(v) for v in s.split(',')] for s in p['shape'].split()])
        onland |= in_poly(E, N, ring)
    water = (Z < LAKE + 0.8) & ~onland
    Z = np.where(water, LAKE, np.maximum(Z, np.where(onland, LAKE + 1.0, LAKE)))
    # soften the stepped shoreline the clamp leaves, then hold the lake flat
    Z = np.where(water, LAKE, np.maximum(smooth(Z, 2), LAKE + 0.3))

    # Horizon grids: 6 m out to 1.5 km around the land, 50 m beyond.
    nE0, nN0, nd, nn = E0 - 1200, N0 + 1200, 6.0, int((NX * D + 2400) / 6)
    Gn = smooth(grid_sample(fine, nE0, nN0, nd, nn, nn), 2)
    Gn = np.maximum(Gn, LAKE)
    cE0, cN0, cd, cn = E0 - FAR, N0 + FAR, 50.0, int((2 * FAR + NX * D) / 50)
    Gc = np.maximum(grid_sample(coarse, cE0, cN0, cd, cn, cn), LAKE)
    # keep the land's own corrected heights inside the near grid
    Gn_land = bilinear(Z, E0, N0, D, *np.meshgrid(nE0 + np.arange(nn) * nd, nN0 - np.arange(nn) * nd))
    inside = np.zeros(Gn.shape, bool)
    iy0, ix0 = int((nN0 - N0) / nd), int((E0 - nE0) / nd)
    inside[iy0:iy0 + NY, ix0:ix0 + NX] = True
    Gn = np.where(inside, Gn_land, Gn)

    dn = np.concatenate([np.geomspace(6, 1100, 70)])
    df = np.geomspace(1150, FAR, 60)
    R = 6371000.0 / (1 - 0.13)
    H = np.zeros((NY, NX, N_AZ), np.float32)
    eye = Z + 1.5  # eye height, roughly where a plant canopy or person is
    for a in range(N_AZ):
        az = math.radians(a * 360 / N_AZ)
        sx, sy = math.sin(az), math.cos(az)
        best = np.full(Z.shape, -90.0)
        for dist, G, g0e, g0n, gd in ((dn, Gn, nE0, nN0, nd), (df, Gc, cE0, cN0, cd)):
            for d in dist:
                z = bilinear(G, g0e, g0n, gd, E + sx * d, N + sy * d) - d * d / (2 * R)
                best = np.maximum(best, np.degrees(np.arctan2(z - eye, d)))
        H[:, :, a] = np.clip(best, 0, 63.75)
        print('azimuth', a, file=sys.stderr)

    gy, gx = np.gradient(Z, D)
    dzdx, dzdy = gx, -gy  # rows run north to south
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    aspect = (np.degrees(np.arctan2(-dzdx, -dzdy)) + 360) % 360

    F = priority_fill(Z, water)
    A = flow_accumulation(F, water)
    twi = np.log((A / D) / np.maximum(np.tan(np.radians(slope)), 0.01))
    twi[water] = 0

    # Hollows and ridges: height against the ring 30 to 90 m around.
    k = 15
    P = np.pad(Z, k, mode='edge')
    acc, cnt = np.zeros(Z.shape), 0
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            if 25 <= (dy * dy + dx * dx) * D * D <= 90 * 90:
                acc += P[k + dy:k + dy + NY, k + dx:k + dx + NX]
                cnt += 1
    tpi = Z - acc / cnt
    tpi[water] = 0

    svf = 1 - np.mean(np.sin(np.radians(H)) ** 2, axis=2)

    out = {
        'note': 'Generated by tools/build_terrain.py. Arrays are row-major, north row first, little-endian base64.',
        'source': 'AWS Terrain Tiles (Terrarium, zoom 15 and 12; in Switzerland mostly SRTM and EU-DEM, about 25 to 30 m detail), shifted +3.4 m to Swiss heights',
        'built': '2026-10-21',
        'e0': E0, 'n0': N0, 'd': D, 'nx': NX, 'ny': NY, 'lake': LAKE, 'n_az': N_AZ,
        'elev': b64(Z.astype('<f4')),
        'slope': b64(slope.astype('<f4')),
        'aspect': b64(aspect.astype('<f4')),
        'twi': b64(twi.astype('<f4')),
        'tpi': b64(tpi.astype('<f4')),
        'svf': b64(svf.astype('<f4')),
        'water': b64(water.astype('u1')),
        'horizon_q': 0.25,
        'horizon': b64(np.round(H / 0.25).astype('u1')),
    }
    json.dump(out, open(os.path.join(ROOT, 'data', 'terrain.json'), 'w'))
    on = onland & ~water
    print('elev on land', Z[on].min(), Z[on].max(), 'slope', np.percentile(slope[on], [10, 50, 90]),
          'twi', np.percentile(twi[on], [10, 50, 90]), 'tpi', np.percentile(tpi[on], [5, 95]),
          'horizon south at house', H[int((N0 - 1209337) / D), int((2673037 - E0) / D), ::4].round(1), file=sys.stderr)


if __name__ == '__main__':
    main()
