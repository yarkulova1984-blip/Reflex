"""Remove the baked-in reflex-map labels and pointer lines from the owner's foot photo
(brand/photos/amt-oct16/foot-map-thumb.jpg -> foot-thumb-clean.png), so no other creator's
educational text or layout is reused (CLAUDE.md §32) and no half-hidden words remain."""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "brand", "photos", "amt-oct16", "foot-map-thumb.jpg")
DST = os.path.join(ROOT, "brand", "photos", "amt-oct16", "foot-thumb-clean.png")

BOXES = [(112, 75, 190, 95), (503, 143, 575, 162), (476, 215, 594, 236), (302, 283, 450, 302),
         (340, 337, 413, 356), (508, 317, 570, 336), (184, 404, 320, 425), (488, 405, 577, 425),
         (300, 448, 342, 468), (443, 448, 461, 468), (480, 455, 552, 475), (427, 505, 474, 525),
         (400, 546, 416, 566), (198, 590, 242, 630), (392, 595, 512, 617), (400, 618, 502, 640),
         (372, 665, 490, 688)]
LINES = [((155, 104), (378, 104)), ((155, 104), (155, 318)), ((155, 104), (272, 178)),
         ((155, 104), (218, 252)), ((155, 104), (484, 192))]


def fill(arr, known):
    """Normalized-convolution fill: coarse estimate everywhere, refined by finer scales
    wherever enough clean pixels are nearby."""
    out = None
    for r in (24, 12, 6, 3, 1.5):
        num = np.stack([_blur(arr[..., c] * known, r) for c in range(3)], -1)
        den = _blur(known, r)[..., None]
        est = num / np.maximum(den, 1e-6)
        if out is None:
            out = est
        else:
            w = np.clip(den / 0.35, 0, 1)
            out = out * (1 - w) + est * w
    return np.where(known[..., None] > 0.5, arr, out)


def remove_lines(arr, half=3.5, reach=6.5):
    """Erase each thin pointer line by interpolating straight across it (perpendicular),
    so toe edges that cross the line continue naturally."""
    arr = arr.copy()
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    for (ax, ay), (bx, by) in LINES:
        dx, dy = bx - ax, by - ay
        L = np.hypot(dx, dy)
        tx, ty = dx / L, dy / L
        nx, ny = -ty, tx
        u = (xx - ax) * tx + (yy - ay) * ty
        sd = (xx - ax) * nx + (yy - ay) * ny
        sel = (np.abs(sd) < half) & (u > -3) & (u < L + 3)
        ys, xs = np.nonzero(sel)
        d = sd[ys, xs]
        p1x, p1y = xs + nx * (reach - d), ys + ny * (reach - d)
        p2x, p2y = xs - nx * (reach + d), ys - ny * (reach + d)

        def samp(px, py):
            px = np.clip(px, 0, w - 1.001); py = np.clip(py, 0, h - 1.001)
            x0, y0 = px.astype(int), py.astype(int)
            fx, fy = (px - x0)[:, None], (py - y0)[:, None]
            return (arr[y0, x0] * (1 - fx) + arr[y0, x0 + 1] * fx) * (1 - fy) + (arr[y0 + 1, x0] * (1 - fx) + arr[y0 + 1, x0 + 1] * fx) * fy
        wgt = ((d + reach) / (2 * reach))[:, None]
        arr[ys, xs] = samp(p2x, p2y) * (1 - wgt) + samp(p1x, p1y) * wgt
    return arr


def _blur(a, r):
    """Separable gaussian blur in NumPy (edge-padded)."""
    k = max(1, int(3 * r))
    x = np.arange(-k, k + 1, dtype=np.float32)
    g = np.exp(-x ** 2 / (2 * r * r))
    g /= g.sum()
    a = a.astype(np.float32)
    a = np.pad(a, ((k, k), (0, 0)), mode="edge")
    a = sum(g[i] * a[i:i + a.shape[0] - 2 * k] for i in range(2 * k + 1))
    a = np.pad(a, ((0, 0), (k, k)), mode="edge")
    return sum(g[i] * a[:, i:i + a.shape[1] - 2 * k] for i in range(2 * k + 1))


def main():
    im = Image.open(SRC).convert("RGB")
    arr = np.asarray(im, np.float32)
    lum = arr @ np.array([0.299, 0.587, 0.114], np.float32)
    local = _blur(lum, 6)
    sat = arr.max(-1) - arr.min(-1)
    mask = np.zeros(lum.shape, bool)
    for x0, y0, x1, y1 in BOXES:
        x0, y0, x1, y1 = x0 - 4, y0 - 4, x1 + 4, y1 + 4
        sub = (lum[y0:y1, x0:x1] > local[y0:y1, x0:x1] + 6) & (sat[y0:y1, x0:x1] < 70)
        mask[y0:y1, x0:x1] |= sub
    m = Image.fromarray((mask * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MaxFilter(7))
    known = (np.asarray(m) < 128).astype(np.float32)
    arr = remove_lines(arr)
    # leftover specks where lines met toe edges
    lum2 = arr @ np.array([0.299, 0.587, 0.114], np.float32)
    spk = lum2 > _blur(lum2, 4) + 12
    yy, xx = np.mgrid[0:lum2.shape[0], 0:lum2.shape[1]].astype(np.float32)
    near = np.zeros(lum2.shape, bool)
    for (ax, ay), (bx, by) in LINES:
        dx, dy = bx - ax, by - ay
        L = np.hypot(dx, dy)
        u = ((xx - ax) * dx + (yy - ay) * dy) / L
        near |= (np.abs((xx - ax) * dy - (yy - ay) * dx) / L < 7) & (u > -8) & (u < L + 8)
    extra = Image.fromarray(((spk & near) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
    known = known * (np.asarray(extra) < 128)
    m = Image.fromarray(np.maximum(np.asarray(m), np.asarray(extra)))
    out = fill(arr, known)
    # grain so the patches don't look plastic
    rng = np.random.default_rng(4)
    out = np.where(known[..., None] > 0.5, out, out + rng.normal(0, 1.6, out.shape))
    soft = np.asarray(m.filter(ImageFilter.GaussianBlur(1.5)), np.float32)[..., None] / 255
    out = arr * (1 - soft) + out * soft
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(DST)
    print(DST)


if __name__ == "__main__":
    main()
