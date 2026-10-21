"""Motion-reklama generatori: 1080x1920, 30fps, ~15s.

Ikki fayl chiqaradi:
  ad.mp4   - toza reklama videosi
  reel.mp4 - Instagram Reels formati (tepada matn, o'rtada reklama)
Matnlar va ranglarni pastdagi CONFIG bo'limida o'zgartirish mumkin.
"""
import math, random, subprocess, sys, wave
import numpy as np
import cairo

# ---------------- CONFIG ----------------
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
W, H, FPS, DUR = 1080, 1920, 30, 15.0
BRAND = "Claude"
WORD_ASK = "savol"
WORD_WRITE = "o’yla"
WORD_DRAFT, WORD_FINAL = "qiyin", "oson"
SLOGAN = ("G’oya sizdan,", "natija — bizdan.")
REEL_CAPTION_1 = ["Claude’ga bitta buyruq berdim:", "“Menga reklama yasab ber”", "", "Natija:"]
REEL_CAPTION_2 = ["Buni qanday qilganimni", "bilmoqchimisiz?", "izohga “VIDEO” deb yozing"]
REEL_SWITCH = 7.2  # sekund: ikkinchi matnga o'tish

BG = (0.957, 0.945, 0.918)
INK = (0.10, 0.10, 0.098)
GREY = (0.62, 0.60, 0.57)
ACC = (0.85, 0.40, 0.25)
SERIF, SANS = "Liberation Serif", "Liberation Sans"
# ----------------------------------------

CX, CY = W / 2, H / 2
N = int(DUR * FPS)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def eo(x):  # ease out cubic
    return 1 - (1 - x) ** 3


def eio(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def eback(x, s=1.7):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def rgb(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0], c[1], c[2], a)


def poly_partial(ctx, pts, frac):
    """Polilinyaning boshidan frac qismini chizadi (path qo'shadi)."""
    if frac <= 0 or len(pts) < 2:
        return None
    d = [0.0]
    for i in range(1, len(pts)):
        d.append(d[-1] + math.dist(pts[i - 1], pts[i]))
    target = d[-1] * clamp(frac)
    ctx.move_to(*pts[0])
    end = pts[0]
    for i in range(1, len(pts)):
        if d[i] <= target:
            ctx.line_to(*pts[i])
            end = pts[i]
        else:
            k = (target - d[i - 1]) / max(1e-9, d[i] - d[i - 1])
            end = (pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * k,
                   pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * k)
            ctx.line_to(*end)
            break
    return end


def font(ctx, size, bold=False, family=SERIF, italic=False):
    ctx.select_font_face(family,
                         cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


def text_c(ctx, s, cx, cy, color=INK, a=1.0):
    e = ctx.text_extents(s)
    ctx.move_to(cx - e.width / 2 - e.x_bearing, cy - e.height / 2 - e.y_bearing)
    rgb(ctx, color, a)
    ctx.show_text(s)
    return e


def spark(ctx, cx, cy, r, rot=0.0, a=1.0, n=10, thick=0.17, color=ACC, wobble=0.0):
    """Original to'q sariq 'uchqun' belgisi: yumaloq uchli nurlar."""
    if r <= 0.5:
        return
    rgb(ctx, color, a)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(n):
        ang = rot + i * 2 * math.pi / n
        ln = r * (1.0 if i % 2 == 0 else 0.8) * (1 + wobble * math.sin(i * 2.3 + rot * 3))
        ctx.set_line_width(r * thick * (1.0 if i % 2 == 0 else 0.85))
        ctx.move_to(cx + math.cos(ang) * r * 0.12, cy + math.sin(ang) * r * 0.12)
        ctx.line_to(cx + math.cos(ang) * ln, cy + math.sin(ang) * ln)
        ctx.stroke()
    ctx.arc(cx, cy, r * 0.2, 0, 2 * math.pi)
    ctx.fill()


def wordmark(ctx, cx, cy, size, reveal=1.0, spark_scale=1.0, rot=0.0):
    font(ctx, size)
    e = ctx.text_extents(BRAND)
    sr = size * 0.36
    gap = size * 0.18
    total = sr * 2 + gap + e.x_advance
    x0 = cx - total / 2
    spark(ctx, x0 + sr, cy - size * 0.28, sr * spark_scale, rot)
    # matnni chapdan o'ngga ochish
    ctx.save()
    ctx.rectangle(x0 + sr * 2 + gap - 5, 0, (e.x_advance + 20) * reveal, H)
    ctx.clip()
    ctx.move_to(x0 + sr * 2 + gap, cy)
    rgb(ctx, INK)
    ctx.show_text(BRAND)
    ctx.restore()


# ---------------- SAHNALAR ----------------
def sc_intro(ctx, t, s):
    sc = eback(seg(t, 0.0, 0.35))
    wordmark(ctx, CX, CY + 40, 150, reveal=eo(seg(t, 0.2, 0.6)), spark_scale=sc, rot=t * 1.2)


def sc_question(ctx, t, s):
    # "?" chiziq bilan chiziladi, nuqtasi to'q sariq bo'lib tushadi
    pts = []
    r = 150
    ox, oy = CX, CY - 260
    for i in range(80):
        a = math.radians(200 + 250 * i / 79)
        pts.append((ox + math.cos(a) * r, oy + math.sin(a) * r))
    last = pts[-1]
    pts += [(last[0], last[1] + 30), (CX, CY + 10), (CX, CY + 90)]
    ctx.set_line_width(58)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    rgb(ctx, INK)
    poly_partial(ctx, pts, eio(seg(t, 0.0, 0.55)))
    ctx.stroke()
    d = seg(t, 0.45, 0.8)
    if d > 0:
        y = CY + 260 - (1 - eback(d, 2.4)) * 300
        rgb(ctx, ACC)
        ctx.arc(CX, y, 52 * eo(min(1, d * 2)), 0, 2 * math.pi)
        ctx.fill()


def sc_ask(ctx, t, s):
    font(ctx, 250, bold=True)
    e1 = ctx.text_extents(WORD_ASK)
    e2 = ctx.text_extents("?")
    total = e1.x_advance + e2.x_advance
    x = CX - total / 2
    y = CY + 80
    a = eo(seg(t, 0, 0.25))
    ctx.move_to(x, y + (1 - a) * 40)
    rgb(ctx, INK, a)
    ctx.show_text(WORD_ASK)
    q = seg(t, 0.3, 0.6)
    if q > 0:
        ctx.save()
        ctx.translate(x + e1.x_advance + e2.x_advance / 2, y - 90)
        ctx.rotate((1 - eback(q)) * 0.6)
        ctx.scale(eback(q), eback(q))
        ctx.move_to(-e2.x_advance / 2, 90)
        rgb(ctx, ACC)
        ctx.show_text("?")
        ctx.restore()
    # nozik konstruksiya chiziqlari
    rgb(ctx, GREY, 0.6)
    ctx.set_line_width(1.5)
    for k, yy in enumerate((y - 175, y, y + 55)):
        f = eo(seg(t, 0.1 + k * 0.08, 0.6 + k * 0.08))
        ctx.move_to(90, yy)
        ctx.line_to(90 + (W - 180) * f, yy)
        ctx.stroke()


rng = random.Random(7)
MOTIF = [[(rng.uniform(40, 360), rng.uniform(-60, 60)) for _ in range(5)] for _ in range(3)]


def sc_kaleido(ctx, t, s):
    ctx.save()
    ctx.translate(CX, CY)
    ctx.rotate(t * 0.9)
    n = 12
    for i in range(n):
        ctx.save()
        ctx.rotate(i * 2 * math.pi / n)
        for j, m in enumerate(MOTIF):
            pts = []
            for k in range(60):
                u = k / 59
                x = sum(p[0] * math.comb(4, q) * u ** q * (1 - u) ** (4 - q) for q, p in enumerate(m))
                y = sum(p[1] * math.comb(4, q) * u ** q * (1 - u) ** (4 - q) for q, p in enumerate(m))
                pts.append((x, y))
            rgb(ctx, INK if j else ACC, 0.85)
            ctx.set_line_width(3 if j else 4)
            poly_partial(ctx, pts, eio(seg(t, 0.05 + j * 0.1, 0.65 + j * 0.1)))
            ctx.stroke()
        ctx.restore()
    ctx.restore()
    rgb(ctx, INK)
    ctx.set_line_width(6)
    ctx.arc(CX, CY, 410, -math.pi / 2, -math.pi / 2 + 2 * math.pi * eio(seg(t, 0, 0.8)))
    ctx.stroke()
    spark(ctx, CX, CY, 70 * eback(seg(t, 0.4, 0.7)), rot=-t * 2)


def sc_write(ctx, t, s):
    # orqada erkin kalligrafik halqalar
    ctx.set_line_width(2.2)
    for k in range(5):
        pts = []
        for i in range(400):
            u = i / 399
            a = u * math.pi * 2 * (2.5 + k * 0.3)
            x = 80 + u * (W - 160) + math.sin(a) * (70 + k * 12)
            y = 430 + k * 38 + math.cos(a * 1.02) * (90 - k * 6) + math.sin(u * 7 + k) * 40
            pts.append((x, y))
        rgb(ctx, INK, 0.55)
        poly_partial(ctx, pts, eio(seg(t, k * 0.06, 0.7 + k * 0.06)))
        ctx.stroke()
    font(ctx, 300, bold=True)
    full = ctx.text_extents(WORD_WRITE)
    n = int(len(WORD_WRITE) * seg(t, 0.1, 0.55) + 0.999)
    sub = WORD_WRITE[:n]
    x = CX - full.x_advance / 2
    y = CY + 230
    ctx.move_to(x, y)
    rgb(ctx, INK)
    ctx.show_text(sub)
    cur = x + ctx.text_extents(sub).x_advance + 14
    if (s * 2.5) % 1 < 0.6 or t < 0.6:
        rgb(ctx, ACC)
        ctx.rectangle(cur, y - 210, 14, 250)
        ctx.fill()


def sc_ring(ctx, t, s):
    n = 36
    R = 340 + 30 * eo(seg(t, 0, 1))
    for i in range(n):
        g = eback(seg(t, i / n * 0.45, i / n * 0.45 + 0.3))
        if g <= 0:
            continue
        a = i * 2 * math.pi / n + t * 1.4
        ctx.save()
        ctx.translate(CX + math.cos(a) * R, CY + math.sin(a) * R)
        ctx.rotate(a + math.pi / 2 + math.sin(s * 3 + i) * 0.3)
        ctx.scale(g, g)
        rgb(ctx, INK)
        ctx.move_to(0, -46)
        ctx.curve_to(26, -20, 16, 30, 0, 46)
        ctx.curve_to(-16, 30, -26, -20, 0, -46)
        ctx.fill()
        ctx.restore()
    p = 1 + 0.25 * math.sin(s * 9)
    rgb(ctx, ACC)
    ctx.arc(CX, CY, 16 * p * eo(seg(t, 0.2, 0.4)), 0, 2 * math.pi)
    ctx.fill()


def sc_morph(ctx, t, s):
    font(ctx, 210, bold=True)
    if t < 0.25:
        sub = WORD_DRAFT
    elif t < 0.5:
        k = seg(t, 0.25, 0.5)
        sub = WORD_DRAFT[:round(len(WORD_DRAFT) * (1 - k))]
    else:
        k = seg(t, 0.52, 0.75)
        sub = WORD_FINAL[:round(len(WORD_FINAL) * k)]
    e = ctx.text_extents(sub) if sub else None
    w = e.x_advance if e else 0
    x = CX - w / 2
    y = CY + 70
    ctx.move_to(x, y)
    rgb(ctx, INK)
    ctx.show_text(sub)
    if t < 0.8:
        rgb(ctx, ACC)
        ctx.rectangle(x + w + 10, y - 150, 11, 185)
        ctx.fill()
    u = eio(seg(t, 0.78, 1.0))
    if u > 0:
        rgb(ctx, ACC)
        ctx.set_line_width(12)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(x, y + 60)
        ctx.line_to(x + w * u, y + 60)
        ctx.stroke()


def sc_spiral(ctx, t, s):
    phi = (1 + 5 ** 0.5) / 2
    size = 760
    x0, y0 = CX - size / 2, CY - size / phi / 2
    x, y, w, h = x0, y0, size, size / phi
    rects, arcs = [], []
    for i in range(9):
        d = i % 4
        sq = min(w, h)
        if d == 0:
            rects.append((x, y, sq, sq)); arcs.append((x + sq, y + sq, sq, math.pi, 1.5 * math.pi)); x += sq; w -= sq
        elif d == 1:
            rects.append((x, y, sq, sq)); arcs.append((x, y + sq, sq, 1.5 * math.pi, 2 * math.pi)); y += sq; h -= sq
        elif d == 2:
            rects.append((x + w - sq, y, sq, sq)); arcs.append((x + w - sq, y, sq, 0, 0.5 * math.pi)); w -= sq
        else:
            rects.append((x, y + h - sq, sq, sq)); arcs.append((x + sq, y + h - sq, sq, 0.5 * math.pi, math.pi)); h -= sq
    ctx.set_line_width(1.6)
    for i, r in enumerate(rects):
        f = eo(seg(t, i * 0.04, i * 0.04 + 0.25))
        rgb(ctx, GREY, 0.7 * f)
        ctx.rectangle(*r)
        ctx.stroke()
    pts = []
    for (ax, ay, rr, a0, a1) in arcs:
        for k in range(40):
            a = a0 + (a1 - a0) * k / 39
            pts.append((ax + math.cos(a) * rr, ay + math.sin(a) * rr))
    rgb(ctx, INK)
    ctx.set_line_width(5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    end = poly_partial(ctx, pts, eio(seg(t, 0.15, 0.9)))
    ctx.stroke()
    if end:
        rgb(ctx, ACC)
        ctx.arc(end[0], end[1], 18, 0, 2 * math.pi)
        ctx.fill()


def sc_bloom(ctx, t, s):
    g = eback(seg(t, 0, 0.45), 2.2)
    r = 30 + 330 * g
    sx = 1 + 0.12 * math.sin(s * 10) * (1 - seg(t, 0.4, 0.9))
    ctx.save()
    ctx.translate(CX, CY)
    ctx.scale(sx, 2 - sx)
    spark(ctx, 0, 0, r, rot=t * 2.4, wobble=0.12 * (1 - seg(t, 0.5, 1)), n=10)
    ctx.restore()


def sc_slogan(ctx, t, s):
    font(ctx, 190, bold=True)
    a = eo(seg(t, 0, 0.3))
    ctx.save()
    ctx.translate(0, (1 - a) * 60)
    text_c(ctx, SLOGAN[0], CX, CY - 90, INK, a)
    ctx.restore()
    font(ctx, 120, italic=True)
    b = eo(seg(t, 0.3, 0.6))
    ctx.save()
    ctx.translate(0, (1 - b) * 60)
    e = text_c(ctx, SLOGAN[1], CX, CY + 110, INK, b)
    ctx.restore()
    if b > 0.9:
        rgb(ctx, ACC)
        ctx.arc(CX + e.width / 2 + 8, CY + 145, 14 * eback(seg(t, 0.6, 0.8)), 0, 2 * math.pi)
        ctx.fill()


def sc_outro(ctx, t, s):
    wordmark(ctx, CX, CY + 40, 150, reveal=eo(seg(t, 0.15, 0.55)),
             spark_scale=1 + 1.4 * (1 - eo(seg(t, 0, 0.25))), rot=t * 1.5)




# ---------------- TEZ "FLASH" KADRLAR ----------------
def fl_globe(ctx, t, s):
    R = 340
    ctx.save()
    ctx.arc(CX, CY, R, 0, 2 * math.pi)
    ctx.clip()
    off = t * 40
    y = -R + (off % 13)
    while y < R:
        ch = math.sqrt(max(0, R * R - y * y))
        lw = 1.2 + 2.6 * clamp((y + R) / (2 * R)) * 0.9
        rgb(ctx, INK)
        ctx.set_line_width(lw)
        ctx.move_to(CX - ch, CY + y)
        for k in range(1, 41):
            x = -ch + 2 * ch * k / 40
            bulge = (1 - (x / max(ch, 1)) ** 2) * 26 * (y / R)
            ctx.line_to(CX + x, CY + y + bulge)
        ctx.stroke()
        y += 13
    ctx.restore()
    rgb(ctx, ACC)
    ctx.set_line_width(7)
    ctx.save()
    ctx.translate(CX, CY)
    ctx.scale(abs(math.cos(t * 2.5 + 0.6)) + 0.05, 1)
    ctx.arc(0, 0, R, 0, 2 * math.pi)
    ctx.restore()
    ctx.stroke()


def fl_halftone(ctx, t, s):
    R, step = 360, 22
    la = 2.2 + t * 2.5
    lx, ly, lz = math.cos(la) * 0.6, -0.55, 0.58
    for gy in range(-R, R + 1, step):
        for gx in range(-R, R + 1, step):
            d2 = gx * gx + gy * gy
            if d2 > R * R:
                continue
            nz = math.sqrt(1 - d2 / (R * R))
            lum = clamp(gx / R * lx + gy / R * ly + nz * lz)
            r = (1 - lum) * step * 0.48
            if r > 0.8:
                rgb(ctx, INK)
                ctx.arc(CX + gx, CY + gy, r, 0, 2 * math.pi)
                ctx.fill()
    rgb(ctx, ACC)
    ctx.arc(CX + 150, CY - 170, 22, 0, 2 * math.pi)
    ctx.fill()


RB = [(random.Random(i).uniform(0.4, 1.0), random.Random(i * 7).uniform(-0.02, 0.02)) for i in range(90)]


def fl_radial(ctx, t, s):
    g = eo(clamp(0.35 + t))
    rgb(ctx, INK)
    ctx.set_line_width(2)
    for i, (ln, jit) in enumerate(RB):
        a = i * 2 * math.pi / len(RB) + jit + t * 0.4
        r1 = 70
        r2 = 70 + 460 * ln * g
        ctx.move_to(CX + math.cos(a) * r1, CY + math.sin(a) * r1)
        ctx.line_to(CX + math.cos(a) * r2, CY + math.sin(a) * r2)
        ctx.stroke()
    rgb(ctx, ACC)
    ctx.arc(CX, CY, 34, 0, 2 * math.pi)
    ctx.fill()


def fl_sgrid(ctx, t, s):
    for r in range(4):
        for c in range(3):
            x = CX + (c - 1) * 300
            y = CY + (r - 1.5) * 330
            k = r * 3 + c
            col = ACC if k == 7 else INK
            spark(ctx, x, y, 95, rot=t * (2 if k % 2 else -2) + k, n=6 + (k % 4) * 2,
                  thick=0.12 + 0.04 * (k % 3), color=col)


def fl_dark(ctx, t, s):
    rgb(ctx, INK)
    ctx.paint()
    spark(ctx, CX, CY, 300 + 40 * t, rot=t * 3, color=BG)
    ctx.set_line_width(3)
    rgb(ctx, BG)
    ctx.arc(CX, CY, 430, 0, 2 * math.pi)
    ctx.stroke()


SCRIB = []
_r = random.Random(3)
_pts = [(CX + _r.uniform(-380, 380), CY + _r.uniform(-520, 520)) for _ in range(9)]
for i in range(len(_pts) - 3):
    p0, p1, p2, p3 = _pts[i:i + 4]
    for k in range(25):
        u = k / 25
        b = [(-u ** 3 + 3 * u ** 2 - 3 * u + 1) / 6, (3 * u ** 3 - 6 * u ** 2 + 4) / 6,
             (-3 * u ** 3 + 3 * u ** 2 + 3 * u + 1) / 6, u ** 3 / 6]
        SCRIB.append((sum(b[j] * q[0] for j, q in enumerate((p0, p1, p2, p3))),
                      sum(b[j] * q[1] for j, q in enumerate((p0, p1, p2, p3)))))


def fl_scribble(ctx, t, s):
    rgb(ctx, INK)
    ctx.set_line_width(9)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    end = poly_partial(ctx, SCRIB, eo(clamp(0.2 + t)))
    ctx.stroke()
    if end:
        rgb(ctx, ACC)
        ctx.arc(end[0], end[1], 26, 0, 2 * math.pi)
        ctx.fill()


def fl_concentric(ctx, t, s):
    for i, r in enumerate(range(40, 520, 40)):
        a0 = t * (3 if i % 2 else -3) + i
        rgb(ctx, ACC if i == 4 else INK)
        ctx.set_line_width(5 if i == 4 else 2.5)
        ctx.arc(CX, CY, r, a0, a0 + 2 * math.pi * (0.55 + 0.4 * clamp(t * 1.4)))
        ctx.stroke()


STUT = [(random.Random(i).uniform(250, 830), random.Random(i + 50).uniform(450, 1470),
         random.Random(i + 99).uniform(50, 260)) for i in range(8)]


def fl_stutter(ctx, t, s):
    i = min(len(STUT) - 1, int(t * len(STUT)))
    x, y, r = STUT[i]
    spark(ctx, x, y, r, rot=i * 0.7)


FIK = ("bir", "ga")


def fl_big(ctx, t, s):
    font(ctx, 600, bold=True)
    a = eo(clamp(t * 2.2))
    e1 = ctx.text_extents(FIK[0])
    e2 = ctx.text_extents(FIK[1])
    ctx.move_to(CX - e1.x_advance / 2 - (1 - a) * 900, CY - 40)
    rgb(ctx, INK)
    ctx.show_text(FIK[0])
    ctx.move_to(CX - e2.x_advance / 2 + (1 - a) * 900, CY + 400)
    ctx.show_text(FIK[1])
    if t > 0.55:
        rgb(ctx, ACC)
        ctx.arc(CX + e2.x_advance / 2 + 50, CY + 370, 40 * eback(seg(t, 0.55, 0.8)), 0, 2 * math.pi)
        ctx.fill()


# ---------------- TEZ SAHNALAR ----------------
def fast_question(ctx, t, s):
    sc_question(ctx, clamp(t * 1.25), s)


def fast_ask(ctx, t, s):
    sc_ask(ctx, clamp(t * 1.6), s)


def fast_write(ctx, t, s):
    sc_write(ctx, clamp(0.15 + t * 1.3), s * 2)


def fast_morph(ctx, t, s):
    sc_morph(ctx, clamp(t * 1.15), s)


def fast_bloom(ctx, t, s):
    sc_bloom(ctx, clamp(t * 1.3), s * 1.5)


def fast_slogan(ctx, t, s):
    font(ctx, 160, bold=True)
    a = eback(seg(t, 0, 0.12))
    ctx.save()
    ctx.translate(CX, CY - 90)
    ctx.scale(a, a)
    text_c(ctx, SLOGAN[0], 0, 0)
    ctx.restore()
    b = eback(seg(t, 0.35, 0.47))
    if b > 0:
        font(ctx, 130, italic=True)
        ctx.save()
        ctx.translate(CX, CY + 120)
        ctx.scale(b, b)
        e = text_c(ctx, SLOGAN[1], 0, 0)
        ctx.restore()
        if t > 0.6:
            rgb(ctx, ACC)
            ctx.arc(CX + e.width / 2 + 10, CY + 158, 15 * eback(seg(t, 0.6, 0.7)), 0, 2 * math.pi)
            ctx.fill()


def flash(fn, lo=0.45):
    return lambda ctx, t, s: fn(ctx, lo + (1 - lo) * t, s)


def fast_outro(ctx, t, s):
    k = seg(t, 0, 0.12)
    if k < 1:
        spark(ctx, CX, CY, 420 * (1 - eio(k)) + 60, rot=t * 6)
        return
    wordmark(ctx, CX, CY + 40, 170, reveal=eo(seg(t, 0.12, 0.35)),
             spark_scale=1 + 0.5 * (1 - eo(seg(t, 0.12, 0.3))), rot=t * 1.2)


BPM = 128
E = 60 / BPM / 2  # sakkizlik nota
TIMELINE = [
    (4, sc_intro), (2, fast_question), (1, fl_scribble), (1, flash(sc_kaleido)), (1, fl_globe),
    (4, fast_ask), (1, flash(sc_ring)), (1, fl_radial), (1, fl_sgrid), (1, fl_dark),
    (3, fast_write), (1, fl_scribble), (1, fl_halftone), (1, fl_concentric), (2, flash(sc_spiral, 0.3)),
    (6, fast_morph), (3, fl_stutter), (2, flash(sc_kaleido, 0.3)), (1, fl_halftone), (1, fl_concentric),
    (3, fl_big), (4, fast_bloom), (6, fast_slogan), (1, flash(sc_ring)), (1, fl_globe), (1, fl_radial),
    (1, fl_sgrid), (1, fl_dark), (8, fast_outro),
]
SCENES = []
_t = 0.0
for n_e, fn in TIMELINE:
    SCENES.append((_t, _t + n_e * E, fn))
    _t += n_e * E
DUR = _t
N = int(round(DUR * FPS))
FLASHES = {fl_globe, fl_halftone, fl_radial, fl_sgrid, fl_dark, fl_scribble, fl_concentric, fl_stutter}

# ---------------- RENDER ----------------
grains = []
for i in range(3):
    nz = np.random.default_rng(i).integers(0, 255, (H, W), dtype=np.uint8)
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[..., 0] = arr[..., 1] = arr[..., 2] = nz
    arr[..., 3] = 255
    surf = cairo.ImageSurface.create_for_data(arr, cairo.FORMAT_ARGB32, W, H)
    grains.append((surf, arr))


def ffmpeg_pipe(path):
    return subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", path],
        stdin=subprocess.PIPE)


ad_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
reel_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
p_ad = ffmpeg_pipe(f"{OUT}/ad_noaudio.mp4")
p_reel = ffmpeg_pipe(f"{OUT}/reel_noaudio.mp4")


def caption(ctx, lines, y0):
    for i, ln in enumerate(lines):
        small = ln == REEL_CAPTION_2[-1]  # oxirgi kichik qator
        font(ctx, 30 if small else 44, family=SANS)
        if ln:
            text_c(ctx, ln, CX, y0 + i * (46 if not small else 40) + (6 if small else 0), (1, 1, 1))


for f in range(N):
    tm = f / FPS
    ctx = cairo.Context(ad_surf)
    rgb(ctx, BG)
    ctx.paint()
    for a, b, fn in SCENES:
        if a <= tm < b or (fn is fast_outro and tm >= a):
            t = clamp((tm - a) / (b - a))
            # har bir kadrda yengil "kamera" yaqinlashuvi
            z = 1 + 0.06 * t if fn in FLASHES else 1 + 0.03 * t
            ctx.save()
            ctx.translate(CX, CY)
            ctx.scale(z, z)
            ctx.translate(-CX, -CY)
            fn(ctx, t, tm - a)
            ctx.restore()
            break
    ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    ctx.set_source_surface(grains[f % 3][0])
    ctx.paint_with_alpha(0.10)
    ctx.set_operator(cairo.OPERATOR_OVER)
    ad_surf.flush()
    p_ad.stdin.write(bytes(ad_surf.get_data()))

    # Reels versiyasi: qo'lda ushlab suratga olingandek yengil tebranish
    rc = cairo.Context(reel_surf)
    rc.set_source_rgb(0.03, 0.03, 0.03)
    rc.paint()
    caption(rc, REEL_CAPTION_1 if tm < REEL_SWITCH else REEL_CAPTION_2, 150)
    sc_ = 0.74
    iw, ih = W * sc_, H * sc_
    ix, iy = (W - iw) / 2, 430
    dx = 5 * math.sin(tm * 1.3) + 2.5 * math.sin(tm * 3.7)
    dy = 4 * math.sin(tm * 1.1 + 1) + 2 * math.sin(tm * 4.3)
    rot = 0.006 * math.sin(tm * 0.9)
    rc.save()
    rc.translate(CX + dx, iy + ih / 2 + dy)
    rc.rotate(rot)
    rc.translate(-iw / 2, -ih / 2)
    for k in range(12, 0, -1):
        rc.set_source_rgba(0, 0, 0, 0.05)
        rc.rectangle(-k * 2, -k * 2 + 10, iw + k * 4, ih + k * 4)
        rc.fill()
    r = 26
    rc.new_sub_path()
    rc.arc(iw - r, r, r, -math.pi / 2, 0)
    rc.arc(iw - r, ih - r, r, 0, math.pi / 2)
    rc.arc(r, ih - r, r, math.pi / 2, math.pi)
    rc.arc(r, r, r, math.pi, 1.5 * math.pi)
    rc.close_path()
    rc.clip()
    rc.scale(sc_, sc_)
    rc.set_source_surface(ad_surf)
    rc.get_source().set_filter(cairo.FILTER_GOOD)
    rc.paint()
    rc.restore()
    reel_surf.flush()
    p_reel.stdin.write(bytes(reel_surf.get_data()))

for p in (p_ad, p_reel):
    p.stdin.close()
    p.wait()

# ---------------- AUDIO (128 BPM) ----------------
SR = 44100
tt = np.arange(int(SR * (DUR + 0.6))) / SR
audio = np.zeros_like(tt)
rng_a = np.random.default_rng(1)
BEAT = 60 / BPM
BAR = BEAT * 4


def add(start, sig):
    i0 = int(start * SR)
    n = min(len(sig), len(audio) - i0)
    if n > 0:
        audio[i0:i0 + n] += sig[:n]


def kick(amp=0.55):
    x = np.arange(int(0.35 * SR)) / SR
    f = 45 + 110 * np.exp(-x * 30)
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 9)


def snare(amp=0.22):
    x = np.arange(int(0.2 * SR)) / SR
    return amp * (rng_a.normal(0, 1, len(x)) * np.exp(-x * 22) + 0.5 * np.sin(2 * np.pi * 190 * x) * np.exp(-x * 30))


def hat(amp=0.06):
    n = rng_a.normal(0, 1, int(0.05 * SR))
    n = np.diff(n, prepend=0)
    return amp * n * np.exp(-np.arange(len(n)) / SR * 70)


def tone(freq, dur, amp, decay, harm=(1, 0.4, 0.15)):
    x = np.arange(int(dur * SR)) / SR
    env = np.minimum(1, x / 0.004) * np.exp(-x * decay)
    return amp * env * sum(h * np.sin(2 * np.pi * freq * (k + 1) * x) for k, h in enumerate(harm))


ROOTS = [55.0, 43.65, 65.41, 49.0]  # A, F, C, G
CHORDS = [[220, 261.6, 329.6, 493.9], [174.6, 220, 261.6, 329.6], [196, 261.6, 329.6, 392], [196, 246.9, 293.7, 392]]
n_bars = int(math.ceil(DUR / BAR))
for b in range(n_bars):
    bs = b * BAR
    root = ROOTS[b % 4]
    last = b == n_bars - 1
    for q in range(4):
        add(bs + q * BEAT, kick(0.7 if last and q == 0 else 0.55))
        if b >= 1 and q in (1, 3) and not last:
            add(bs + q * BEAT, snare())
    for e8 in range(8):
        if not last or e8 == 0:
            add(bs + e8 * BEAT / 2 + 0.01, hat(0.07 if e8 % 2 else 0.04))
            add(bs + e8 * BEAT / 2, tone(root * (2 if e8 % 2 else 1), BEAT / 2, 0.16, 7, (1, 0.6, 0.3)))
    # arpedjio (16-lik) 2-bardan boshlab
    if b >= 1 and not last:
        ch = CHORDS[b % 4]
        for k in range(16):
            add(bs + k * BEAT / 4, tone(ch[(k * 3) % 4] * 2, 0.25, 0.045, 14))
    # pad
    x = np.arange(int(BAR * SR)) / SR
    env = np.minimum(1, x / 0.15) * np.minimum(1, (x[-1] - x) / 0.2 + 1e-3)
    add(bs, sum(0.022 * env * np.sin(2 * np.pi * fq * x) for fq in CHORDS[b % 4]))
# kesimlardagi "tik" ovozlar
for a, b, fn in SCENES:
    if fn in FLASHES:
        add(a, tone(2400, 0.04, 0.05, 80, (1,)))
    else:
        add(a, tone(880 if fn is not fast_outro else 440, 1.2, 0.09, 3.5))
# yozish sahnalarida klik
for a, b, fn in SCENES:
    if fn in (fast_write, fast_morph):
        for k in range(10):
            add(a + (b - a) * (0.08 + k * 0.07), 0.05 * rng_a.normal(0, 1, 500) * np.exp(-np.arange(500) / 70))
# yakuniy kadrdan oldin "riser"
rs = SCENES[-1][0]
x = np.arange(int(BAR * SR)) / SR
nz = rng_a.normal(0, 1, len(x))
nz = np.convolve(nz, np.ones(6) / 6, mode="same")
add(rs - BAR, 0.12 * nz * (x / x[-1]) ** 2)
audio = audio[:int(DUR * SR)]
tt = tt[:len(audio)]
fade = np.minimum(1, np.minimum(tt / 0.02, (DUR - tt) / 0.6))
audio = np.tanh(audio * 1.4) * fade
audio /= np.max(np.abs(audio)) / 0.89
st = np.stack([audio, np.roll(audio, 180) * 0.9 + audio * 0.1], axis=1)
with wave.open(f"{OUT}/music.wav", "wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((st * 32767).astype(np.int16).tobytes())

for name in ("ad", "reel"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{OUT}/{name}_noaudio.mp4", "-i", f"{OUT}/music.wav",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", f"{OUT}/{name}.mp4"], check=True)
print("tayyor", round(DUR, 2), "s,", len(SCENES), "kadr")
