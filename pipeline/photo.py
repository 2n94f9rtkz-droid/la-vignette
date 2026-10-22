"""Recadre automatiquement le visage et applique l'effet vignette (bichromie bleu/crème + trame + grain).
Usage : python photo.py <source> <sortie.png>"""
import sys, numpy as np, cv2
from PIL import Image, ImageOps, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
W, H = 668, 476
im = Image.open(src).convert('RGB')
g0 = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
faces = []
for name in ['haarcascade_frontalface_default.xml', 'haarcascade_frontalface_alt2.xml', 'haarcascade_profileface.xml']:
    cas = cv2.CascadeClassifier(cv2.data.haarcascades + name)
    f = cas.detectMultiScale(g0, 1.06, 5, minSize=(max(20, im.width // 16),) * 2)
    # un visage est dans la moitié haute de la photo (portrait ou plan en pied)
    faces += [tuple(v) for v in f if v[1] + v[3] / 2 < im.height * 0.5]
    if faces: break
if faces:
    mw = max(f[2] for f in faces)
    faces = [min([f for f in faces if f[2] >= 0.6 * mw], key=lambda f: f[1])]  # le plus haut = la tête
if faces:
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    cx, cy, fw = x + w / 2, y + h / 2, w
else:  # pas de visage détecté : haut centré de l'image
    fw = im.width * 0.3; cx = im.width / 2; cy = min(im.height * 0.22, im.width * 0.3)
cw = min(fw * 2.6, im.width); ch = cw * H / W
if ch > im.height: ch = im.height; cw = ch * W / H
box = [cx - cw / 2, cy - ch * 0.42, cx + cw / 2, cy + ch * 0.58]
if box[0] < 0: box[2] -= box[0]; box[0] = 0
if box[2] > im.width: box[0] -= box[2] - im.width; box[2] = im.width
if box[1] < 0: box[3] -= box[1]; box[1] = 0
if box[3] > im.height: box[1] -= box[3] - im.height; box[3] = im.height
crop = im.crop([int(v) for v in box]).resize((W, H), Image.LANCZOS)
g = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(4, 4)).apply(np.array(crop.convert('L')))
g = np.array(ImageOps.autocontrast(Image.fromarray(g), cutoff=1)).astype(float) / 255
g = np.clip((g - 0.5) * 1.15 + 0.55, 0, 1) ** 0.85
ink = np.array([22, 40, 110.]); mid = np.array([27, 58, 140.]); paper = np.array([240, 229, 205.])
t = g[..., None]
col = np.where(t < 0.5, ink + (mid - ink) * (t / 0.5), mid + (paper - mid) * ((t - 0.5) / 0.5))
yy, xx = np.mgrid[0:H, 0:W]; p = 6.0
dot = (np.cos(2 * np.pi * (xx + yy) / p) * np.cos(2 * np.pi * (xx - yy) / p) + 1) / 2
mask = (dot < (0.15 + 0.85 * (1 - g))).astype(float)
mask = np.array(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))) / 255
k = 0.28 * (1 - mask)[..., None]
out = col * (1 - k) + paper * k + np.random.default_rng(0).normal(0, 4, col.shape)
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst)
print('visage détecté' if faces else 'pas de visage, recadrage par défaut', dst)
