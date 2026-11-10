#!/usr/bin/env python3
"""Animated soccer-pitch banner for the profile README.

A top-down, dot-style homage to Rooney's bicycle kick (Man Utd 2-1 Man City,
12 Feb 2011): a long ball out to Nani, his cross deflects off a defender, and
Rooney's overhead kick flies into the top corner (14 s loop). Positions are a
rough reconstruction, not tracking data.

The animation is plain SMIL, so it plays inside GitHub's <img> rendering.
Text is converted to outlines, so the banner looks the same on every machine.

    python3 scripts/make_banner.py -o assets/banner.svg
"""
import argparse
import math

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

# ------------------------------------------------------------------ layout
T = 14.0                                  # loop length (s)
W = 1200                                  # banner width (px)
X0, X1, Y0, Y1 = -4.0, 109.0, 12.0, 56.0  # visible window of a 105 x 68 m pitch
S = W / (X1 - X0)                         # px per metre
H = round((Y1 - Y0) * S)
PLAY_END, RESET_END = 12.4, 13.2          # fade out 11.6-12.4, reset hidden, fade in 13.2-14.0

CROSS_T, DEFLECT_T = 6.2, 6.25            # Nani crosses, the ball clips the defender
CONTACT_T = 7.6                           # overhead kick
GOAL_T, NET_END = 7.95, 8.25

NAME = "SONGYUN JEONG"
TAGLINE = "Sports Analytics × Machine Learning"
CAPTION = "Rooney 78′ · Man Utd 2–1 Man City · Feb 2011"

RED, RED_GK, BLUE, BLUE_GK = "#da291c", "#facc15", "#6cabdd", "#a855f7"
NUMBERS = {"AST": "10", "ARW": "17"}      # Rooney, Nani


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def fmt(v, digits=2):
    s = f"{v:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def hermite(keys):
    """Smooth path through (t, x, y) keys, starting from rest."""
    ts = [k[0] for k in keys]
    ps = [(k[1], k[2]) for k in keys]
    n = len(keys)
    ms = []
    for i in range(n):
        if i == 0 or n == 1:
            ms.append((0.0, 0.0))
        elif i == n - 1:
            ms.append(tuple((ps[i][j] - ps[i - 1][j]) / (ts[i] - ts[i - 1]) for j in (0, 1)))
        else:
            ms.append(tuple(0.5 * ((ps[i + 1][j] - ps[i][j]) / (ts[i + 1] - ts[i])
                                   + (ps[i][j] - ps[i - 1][j]) / (ts[i] - ts[i - 1])) for j in (0, 1)))

    def f(t):
        if t <= ts[0]:
            return ps[0]
        if t >= ts[-1]:
            return ps[-1]
        i = max(k for k in range(n - 1) if ts[k] <= t)
        h = ts[i + 1] - ts[i]
        u = (t - ts[i]) / h
        h00, h10 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u
        h01, h11 = -2 * u**3 + 3 * u**2, u**3 - u**2
        return tuple(h00 * ps[i][j] + h10 * h * ms[i][j] + h01 * ps[i + 1][j] + h11 * h * ms[i + 1][j]
                     for j in (0, 1))

    return f


def unit(dx, dy):
    n = math.hypot(dx, dy)
    return (1.0, 0.0) if n < 1e-6 else (dx / n, dy / n)


# ------------------------------------------------------- scripted players
# Red attacks to the right. Keys are (t, x, y) in metres; players in the move
# follow these, everyone else reacts to the ball (see simulate()).
KEYS = {
    "LCB": [(0.0, 24.0, 30.0), (0.5, 24.0, 30.0)],                                   # Vidic
    "DM": [(0.0, 37.5, 37.8), (0.5, 38.6, 37.2), (1.4, 41.0, 36.4), (1.7, 41.4, 36.3)],  # Scholes
    "RW": [(0.0, 60.0, 52.8), (1.7, 63.5, 53.0), (3.2, 66.5, 53.0), (4.6, 76.0, 52.4),     # Nani
           (CROSS_T, 85.8, 51.3), (6.5, 86.5, 51.2), (7.2, 87.0, 51.6)],
    "ST": [(0.0, 63.0, 35.5), (1.7, 66.0, 35.0), (3.2, 71.0, 35.5), (5.0, 82.0, 36.5),     # Rooney
           (CROSS_T, 90.0, 37.0), (6.9, 93.0, 36.0), (7.35, 94.3, 35.0), (CONTACT_T, 94.6, 34.7),
           (7.8, 94.5, 34.6), (8.4, 94.9, 35.6), (9.4, 97.0, 41.0), (10.6, 99.0, 47.5),
           (PLAY_END, 99.8, 50.5)],
}
KEYS_B = {  # the full-back who gets to Nani and deflects the cross
    "D4": [(0.0, 73.0, 46.8), (1.7, 76.0, 48.5), (3.2, 80.5, 50.0), (4.6, 83.0, 50.6),
           (5.6, 86.0, 50.6), (CROSS_T, 87.6, 50.4), (6.32, 87.9, 50.2), (6.9, 88.8, 50.3),
           (CONTACT_T, 89.6, 49.6), (8.4, 90.2, 48.8)],
}
TRACK = {name: hermite(keys) for name, keys in KEYS.items()}
TEND = {name: keys[-1][0] for name, keys in KEYS.items()}
TRACK_B = {name: hermite(keys) for name, keys in KEYS_B.items()}
TEND_B = {name: keys[-1][0] for name, keys in KEYS_B.items()}


def at_feet(name, t, running):
    x, y = TRACK[name](t)
    if running:
        (x1, y1), (x2, y2) = TRACK[name](t - 0.05), TRACK[name](t + 0.05)
        ux, uy = unit(x2 - x1, y2 - y1)
    else:
        ux, uy = 1.0, 0.0
    return (x + 0.6 * ux, y + 0.6 * uy)


def _deflect_point():
    dx, dy = TRACK_B["D4"](DEFLECT_T)
    fx, fy = at_feet("RW", CROSS_T, True)
    ux, uy = unit(fx - dx, fy - dy)
    return (dx + 0.75 * ux, dy + 0.75 * uy)


DEFLECT_P = _deflect_point()
CONTACT_P = (TRACK["ST"](CONTACT_T)[0] + 0.45, TRACK["ST"](CONTACT_T)[1] - 0.15)
GOAL_P, NET_P = (105.0, 31.3), (106.3, 31.1)

# ball: (start, end, kind, arg)
EVENTS = [
    (0.0, 0.5, "hold", "LCB"),
    (0.5, 1.4, "pass", None),
    (1.4, 1.7, "hold", "DM"),
    (1.7, 3.2, "loft", None),
    (3.2, CROSS_T, "carry", "RW"),
    (CROSS_T, DEFLECT_T, "to", DEFLECT_P),
    (DEFLECT_T, CONTACT_T, "to", CONTACT_P),
    (CONTACT_T, GOAL_T, "to", GOAL_P),
    (GOAL_T, NET_END, "net", NET_P),
    (NET_END, PLAY_END, "rest", NET_P),
]

A_BASE = {  # red shape while building up from the back
    "GK": (6.0, 34.0), "LCB": (21.0, 27.0), "RCB": (22.0, 41.0), "LB": (34.0, 16.5),
    "RB": (33.0, 51.5), "DM": (31.0, 35.5), "LCM": (43.0, 25.0), "RCM": (42.0, 44.0),
    "LW": (55.0, 18.0), "ST": (62.0, 34.5), "RW": (60.0, 52.4),
}
B_BASE = {  # blue 4-4-2 block when the ball is at the centre spot
    "GK": (103.3, 34.0),
    "D1": (84.0, 20.5), "D2": (85.5, 30.0), "D3": (85.5, 38.5), "D4": (84.0, 48.0),
    "M1": (71.0, 19.0), "M2": (69.5, 29.5), "M3": (69.5, 38.5), "M4": (71.0, 49.0),
    "F1": (57.0, 30.0), "F2": (58.0, 39.0),
}
CELEBRATE = ["RW", "LCM", "LW", "RCM", "LB", "DM"]
AIR_HOLD = {"M4": (84.0, 46.5)}  # keeps the helping midfielder out from under the cross


def ease_pass(u):
    return 0.35 * u + 0.65 * (1 - (1 - u) ** 2)


def ball_play(t):
    for k, (t0, t1, kind, arg) in enumerate(EVENTS):
        if t <= t1 or k == len(EVENTS) - 1:
            break
    u = 0.0 if t1 == t0 else clamp((t - t0) / (t1 - t0), 0.0, 1.0)
    if kind == "hold":
        return at_feet(arg, t, False)
    if kind == "carry":
        return at_feet(arg, t, True)
    if kind in ("pass", "loft"):
        a, b = ball_play(t0 - 1e-6), ball_play(t1 + 1e-6)
        e = ease_pass(u)
        return (a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e)
    if kind == "to":
        a = ball_play(t0 - 1e-6)
        return (a[0] + (arg[0] - a[0]) * u, a[1] + (arg[1] - a[1]) * u)
    if kind == "net":
        a = EVENTS[k - 1][3]
        e = 1 - (1 - u) ** 2
        return (a[0] + (arg[0] - a[0]) * e, a[1] + (arg[1] - a[1]) * e)
    return arg  # rest: ball sits in the net


def ball_at(t):
    if t <= PLAY_END:
        return ball_play(t)
    a, b = ball_play(PLAY_END), ball_play(0.0)
    u = clamp((t - PLAY_END) / (RESET_END - PLAY_END), 0.0, 1.0)
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)


def ball_height(t):
    """Drawn size of the ball (1 = on the grass); larger means higher."""
    def phase(t0, t1):
        return (t - t0) / (t1 - t0) if t0 < t < t1 else None
    if (u := phase(1.7, 3.2)) is not None:
        return 1.0 + 0.45 * math.sin(math.pi * u)
    if (u := phase(CROSS_T, DEFLECT_T)) is not None:
        return 1.0 + 0.15 * u
    if (u := phase(DEFLECT_T, CONTACT_T)) is not None:       # looping deflection
        return 1.15 + 0.23 * u + 0.55 * math.sin(math.pi * u)
    if (u := phase(CONTACT_T, GOAL_T)) is not None:          # volley toward the top corner
        return 1.38 - 0.10 * u
    if (u := phase(GOAL_T, NET_END)) is not None:
        return 1.28 - 0.18 * u
    return 1.0


def rooney_lift(t):
    """Rooney leaves the ground for the overhead kick and lands on his back."""
    keys = [(0.0, 1.0), (7.38, 1.0), (7.55, 1.2), (7.72, 0.9), (8.3, 1.0), (T, 1.0)]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0)
            return a + (b - a) * (0.5 - 0.5 * math.cos(math.pi * u))
    return 1.0


# --------------------------------------------------------------- reactions
def a_target(name, ball, line):
    xb, yb = ball
    if name == "GK":
        return (clamp(6.0 + 0.19 * (xb - 22.0), 6.0, 18.0), 34.0 + 0.1 * (yb - 34.0))
    dx = clamp(0.62 * (xb - 22.0), 0.0, 40.0)
    bx, by = A_BASE[name]
    x, y = bx + dx, by + 0.12 * (yb - 34.0)
    if xb > 70:  # final third: wide players tuck in
        k = min((xb - 70) / 15, 1.0)
        y += {"LW": 7.0, "RCM": -3.0, "LCM": 2.0}.get(name, 0.0) * k
    return (min(x, line - 0.6), clamp(y, 14.0, 54.0))


def b_target(name, ball):
    xb, yb = ball
    if name == "GK":
        return (103.3, clamp(34.0 + 0.25 * (yb - 34.0), 31.5, 36.5))
    bx, by = B_BASE[name]
    dx = 0.40 * (xb - 52.5)
    cap = {"D": 96.0, "M": 88.0, "F": 74.0}[name[0]]
    shift = 0.25 if name[0] == "F" else 0.35
    return (min(bx + dx, cap), clamp(by + shift * (yb - 34.0), 14.0, 54.0))


def keep_apart(k, target, pos, gap=2.4):
    """Nudge a target away from nearby players so dots do not overlap."""
    tx, ty = target
    px, py = pos[k]
    for q, (qx, qy) in pos.items():
        d = math.hypot(px - qx, py - qy)
        if q != k and 1e-6 < d < gap:
            tx += (px - qx) / d * (gap - d) * 1.2
            ty += (py - qy) / d * (gap - d) * 1.2
    return (tx, ty)


def separate(pos, fixed, gap=1.9):
    """Hard minimum distance between dots; scripted players are never moved."""
    keys = list(pos)
    for _ in range(2):
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                if a in fixed and b in fixed:
                    continue
                (ax, ay), (bx, by) = pos[a], pos[b]
                d = math.hypot(ax - bx, ay - by)
                if d >= gap:
                    continue
                ux, uy = ((ax - bx) / d, (ay - by) / d) if d > 1e-6 else (0.0, 1.0)
                push = gap - d
                if a in fixed:
                    pos[b] = (bx - ux * push, by - uy * push)
                elif b in fixed:
                    pos[a] = (ax + ux * push, ay + uy * push)
                else:
                    pos[a] = (ax + ux * push / 2, ay + uy * push / 2)
                    pos[b] = (bx - ux * push / 2, by - uy * push / 2)


def step(p, v, target, tau, vmax, amax, dt):
    dvx = (target[0] - p[0]) / tau
    dvy = (target[1] - p[1]) / tau
    n = math.hypot(dvx, dvy)
    if n > vmax:
        dvx, dvy = dvx * vmax / n, dvy * vmax / n
    ax, ay = dvx - v[0], dvy - v[1]
    n = math.hypot(ax, ay)
    if n > amax * dt:
        ax, ay = ax * amax * dt / n, ay * amax * dt / n
    v = (v[0] + ax, v[1] + ay)
    return (p[0] + v[0] * dt, p[1] + v[1] * dt), v


def simulate(dt=0.02):
    reds = list(A_BASE)
    blues = list(B_BASE)
    b_out = [n for n in blues if n != "GK"]
    ball0 = ball_at(0.0)
    pos, vel = {}, {}
    for n in reds:
        pos["A" + n] = TRACK[n](0.0) if n in TRACK else a_target(n, ball0, 84.0)
    for n in blues:
        pos["B" + n] = TRACK_B[n](0.0) if n in TRACK_B else b_target(n, ball0)
    for k in pos:
        vel[k] = (0.0, 0.0)
    separate(pos, {"A" + n for n in TRACK} | {"B" + n for n in TRACK_B})

    hist = {k: [] for k in pos}
    presser, dive = None, None
    steps = int(round(PLAY_END / dt))
    for i in range(steps + 1):
        t = i * dt
        ball = ball_at(t)
        in_air = DEFLECT_T <= t < CONTACT_T   # defenders head for where the cross will land
        def_ball = CONTACT_P if in_air else ball
        line = max(pos["B" + n][0] for n in b_out)
        if in_air:
            presser = None
        elif i % int(round(0.4 / dt)) == 0 and t < GOAL_T:
            presser = min(b_out, key=lambda n: math.dist(pos["B" + n], ball))
        for k in pos:
            hist[k].append(pos[k])
        for n in reds:
            k = "A" + n
            if n in TRACK and t < TEND[n]:
                (x1, y1), (x2, y2) = TRACK[n](t), TRACK[n](t + dt)
                pos[k], vel[k] = (x2, y2), ((x2 - x1) / dt, (y2 - y1) / dt)
                continue
            if t >= GOAL_T + 0.2 and n in CELEBRATE:
                sx, sy = pos["AST"]
                ang = 2 * math.pi * CELEBRATE.index(n) / len(CELEBRATE) + 0.4
                target, vmax = (sx + 2.2 * math.cos(ang), sy + 2.2 * math.sin(ang)), 6.5
            elif t >= GOAL_T:
                target, vmax = pos[k], 3.0
            else:
                target, vmax = a_target(n, ball, line), 7.0
            target = keep_apart(k, target, pos)
            pos[k], vel[k] = step(pos[k], vel[k], target, 0.6, vmax, 5.0, dt)
        for n in blues:
            k = "B" + n
            if n in TRACK_B and t < TEND_B[n]:
                (x1, y1), (x2, y2) = TRACK_B[n](t), TRACK_B[n](t + dt)
                pos[k], vel[k] = (x2, y2), ((x2 - x1) / dt, (y2 - y1) / dt)
                continue
            if n == "GK":
                if t >= CONTACT_T - 0.05:  # late dive toward the top corner
                    if dive is None:
                        x0, y0 = pos[k]
                        dive = hermite([(CONTACT_T - 0.05, x0, y0), (7.92, 103.9, 33.8), (8.3, 104.0, 33.4),
                                        (11.0, 103.8, 33.5), (PLAY_END, 103.8, 33.5)])
                    pos[k] = dive(t + dt)
                    continue
                pos[k], vel[k] = step(pos[k], vel[k], b_target(n, ball), 0.3, 5.0, 8.0, dt)
                continue
            if t >= GOAL_T:
                target, tau, vmax = pos[k], 0.6, 2.5
            elif n == presser:
                gx, gy = unit(105.0 - ball[0], 34.0 - ball[1])
                target, tau, vmax = (ball[0] + 2.6 * gx, ball[1] + 2.6 * gy), 0.35, 7.5
            elif in_air and n in AIR_HOLD:
                target, tau, vmax = AIR_HOLD[n], 0.6, 7.0
            else:
                target, tau, vmax = b_target(n, def_ball), 0.6, 7.0
            target = keep_apart(k, target, pos)
            pos[k], vel[k] = step(pos[k], vel[k], target, tau, vmax, 5.0, dt)
        if t < GOAL_T + 0.2:
            fixed = ({"A" + n for n in TRACK if t + dt < TEND[n]}
                     | {"B" + n for n in TRACK_B if t + dt < TEND_B[n]}
                     | ({"BGK"} if dive else set()))
            separate(pos, fixed)

    def track(k):
        h = hist[k]

        def f(t):
            if t <= PLAY_END:
                x = clamp(t / dt, 0, len(h) - 1)
                i = min(int(x), len(h) - 2)
                u = x - i
                return tuple(h[i][j] + (h[i + 1][j] - h[i][j]) * u for j in (0, 1))
            a, b = h[-1], h[0]
            u = clamp((t - PLAY_END) / (RESET_END - PLAY_END), 0.0, 1.0)
            return tuple(a[j] + (b[j] - a[j]) * u for j in (0, 1))

        return f

    return {k: track(k) for k in hist}


# -------------------------------------------------------------------- text
def text_outline(font_path, text, size, spacing=0.0):
    font = TTFont(font_path)
    glyphs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    scale = size / font["head"].unitsPerEm
    kern = {}
    if "kern" in font:
        for sub in font["kern"].kernTables:
            kern.update(getattr(sub, "kernTable", {}))
    x, prev, parts = 0.0, None, []
    for ch in text:
        g = cmap[ord(ch)]
        if prev is not None:
            x += kern.get((prev, g), 0) * scale
        pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        glyphs[g].draw(TransformPen(pen, (scale, 0, 0, -scale, x, 0)))
        parts.append(pen.getCommands())
        x += hmtx[g][0] * scale + spacing
        prev = g
    return " ".join(p for p in parts if p), x - spacing


# --------------------------------------------------------------------- svg
def anim_translate(f, step_s):
    n = int(round(T / step_s))
    vals = ";".join(f"{fmt(x)},{fmt(y)}" for x, y in (f(i * step_s) for i in range(n + 1)))
    return (f'<animateTransform attributeName="transform" type="translate" dur="{fmt(T)}s" '
            f'repeatCount="indefinite" values="{vals}"/>')


def anim_values(attr, f, step_s, kind=None):
    n = int(round(T / step_s))
    vals = ";".join(f(i * step_s) for i in range(n + 1))
    if kind:
        return (f'<animateTransform attributeName="transform" type="{kind}" dur="{fmt(T)}s" '
                f'repeatCount="indefinite" values="{vals}"/>')
    return f'<animate attributeName="{attr}" dur="{fmt(T)}s" repeatCount="indefinite" values="{vals}"/>'


def pitch_svg():
    out = []
    w = 105.0 / 20
    for i in range(-1, 22):
        out.append(f'<rect x="{fmt(i * w)}" y="{fmt(Y0 - 1)}" width="{fmt(w + 0.02)}" '
                   f'height="{fmt(Y1 - Y0 + 2)}" fill="{"#3e8e48" if i % 2 else "#378343"}"/>')
    ln = 'fill="none" stroke="#fff" stroke-opacity=".8" stroke-width=".15"'
    top, bot = Y0 - 1, Y1 + 1
    out.append(f'<g {ln}>')
    out.append(f'<path d="M0 {fmt(top)}V{fmt(bot)}M105 {fmt(top)}V{fmt(bot)}M52.5 {fmt(top)}V{fmt(bot)}"/>')
    out.append('<circle cx="52.5" cy="34" r="9.15"/>')
    out.append('<path d="M0 13.84H16.5V54.16H0M105 13.84H88.5V54.16H105"/>')
    out.append('<path d="M0 24.84H5.5V43.16H0M105 24.84H99.5V43.16H105"/>')
    out.append('<path d="M16.5 26.688A9.15 9.15 0 0 1 16.5 41.312M88.5 26.688A9.15 9.15 0 0 0 88.5 41.312"/>')
    out.append("</g>")
    out.append('<g fill="#fff" fill-opacity=".85"><circle cx="52.5" cy="34" r=".3"/>'
               '<circle cx="11" cy="34" r=".25"/><circle cx="94" cy="34" r=".25"/></g>')
    net = []
    for gx0 in (-2.0, 105.0):
        for k in range(1, 4):
            net.append(f"M{fmt(gx0 + k * 0.5)} 30.34V37.66")
        for k in range(1, 15):
            net.append(f"M{fmt(gx0)} {fmt(30.34 + k * 0.488)}H{fmt(gx0 + 2)}")
    out.append(f'<path d="{"".join(net)}" stroke="#fff" stroke-opacity=".28" stroke-width=".06"/>')
    out.append('<g fill="#fff" fill-opacity=".07" stroke="#fff" stroke-width=".18">'
               '<rect x="-2" y="30.34" width="2" height="7.32"/><rect x="105" y="30.34" width="2" height="7.32"/></g>')
    return "\n".join(out)


def build(font_bold, font_regular):
    tracks = simulate()

    def k_times(*ts):
        return ";".join(fmt(t / T, 4) for t in ts)

    # ball trail: passes solid, carries dashed, revealed as the ball travels
    dt_b = 0.05
    nb = int(round(T / dt_b))
    pts = [ball_at(i * dt_b) for i in range(nb + 1)]
    play_n = int(round(NET_END / dt_b))
    cum = [0.0]
    for i in range(1, play_n + 1):
        cum.append(cum[-1] + math.dist(pts[i - 1], pts[i]))
    total = cum[-1]
    dash = total + 2.0
    offs = [dash if i * dt_b > PLAY_END + 1e-9 else dash - cum[min(i, play_n)] for i in range(nb + 1)]
    reveal = "M" + "L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts[: play_n + 1])
    solid, dashed = [], []
    for t0, t1, kind, _ in EVENTS:
        if kind in ("pass", "loft", "to", "net"):
            a, b = ball_at(t0 + 1e-6), ball_at(t1 - 1e-6)
            solid.append(f"M{fmt(a[0])} {fmt(a[1])}L{fmt(b[0])} {fmt(b[1])}")
        elif kind == "carry":
            seg = [ball_at(t0 + k * (t1 - t0) / 20) for k in range(21)]
            dashed.append("M" + "L".join(f"{fmt(x)} {fmt(y)}" for x, y in seg))

    fade = (f'<animate attributeName="opacity" dur="{fmt(T)}s" repeatCount="indefinite" values="1;1;0;0;1" '
            f'keyTimes="{k_times(0, 11.6, PLAY_END, RESET_END, T)}"/>')

    def number(text):
        d, w = text_outline(font_bold, text, 0.95)
        return f'<path transform="translate({fmt(-w / 2, 3)},.34)" d="{d}" fill="#fff"/>'

    players = []
    order = [k for k in tracks if k.startswith("B")] + [k for k in tracks if k.startswith("A")]
    for k in order:
        color = {"AGK": RED_GK, "BGK": BLUE_GK}.get(k, RED if k[0] == "A" else BLUE)
        x0, y0 = tracks[k](0.0)
        body = f'<circle r=".85" fill="{color}" stroke="#fff" stroke-width=".16"/>{number(NUMBERS[k]) if k in NUMBERS else ""}'
        if k == "AST":  # Rooney jumps, flips and lands
            shadow = anim_values(None, lambda t: f"{fmt(.22 + 2.2 * (rooney_lift(t) - 1))},"
                                                 f"{fmt(.3 + 2.8 * (rooney_lift(t) - 1))}", 0.05, "translate")
            lift = anim_values(None, lambda t: fmt(rooney_lift(t), 3), 0.05, "scale")
            flip = (f'<g opacity="0"><animate attributeName="opacity" dur="{fmt(T)}s" repeatCount="indefinite" '
                    f'values="0;0;1;1;0;0" keyTimes="{k_times(0, 7.38, 7.44, 7.72, 7.85, T)}"/>'
                    f'<animateTransform attributeName="transform" type="rotate" dur="{fmt(T)}s" repeatCount="indefinite" '
                    f'values="0;0;360;360" keyTimes="{k_times(0, 7.4, 7.8, T)}"/>'
                    f'<path d="M-1.55 0A1.55 1.55 0 0 1 1.55 0" fill="none" stroke="#fff" stroke-width=".2" '
                    f'stroke-linecap="round"/><path d="M1.1 -.35L1.55 .15L2 -.35" fill="none" stroke="#fff" '
                    f'stroke-width=".2" stroke-linecap="round" stroke-linejoin="round"/></g>')
            players.append(
                f'<g transform="translate({fmt(x0)},{fmt(y0)})">{anim_translate(tracks[k], 0.1)}'
                f'<g>{shadow}<circle r=".85" fill="#000" fill-opacity=".25"/></g>'
                f'<g>{lift}{body}</g>{flip}</g>')
            continue
        players.append(
            f'<g transform="translate({fmt(x0)},{fmt(y0)})">{anim_translate(tracks[k], 0.1)}'
            f'<circle cx=".22" cy=".3" r=".85" fill="#000" fill-opacity=".25"/>{body}</g>')

    scale_vals = ";".join(fmt(ball_height(i * dt_b), 3) for i in range(nb + 1))
    shadow_vals = ";".join(f"{fmt(.22 + 2.4 * (ball_height(i * dt_b) - 1))},{fmt(.3 + 3.0 * (ball_height(i * dt_b) - 1))}"
                           for i in range(nb + 1))
    bx0, by0 = ball_at(0.0)
    ball = (f'<g transform="translate({fmt(bx0)},{fmt(by0)})">{anim_translate(ball_at, dt_b)}'
            f'<g><animateTransform attributeName="transform" type="translate" dur="{fmt(T)}s" '
            f'repeatCount="indefinite" values="{shadow_vals}"/>'
            f'<ellipse rx=".6" ry=".46" fill="#000" fill-opacity=".3"/></g>'
            f'<g><animateTransform attributeName="transform" type="scale" dur="{fmt(T)}s" '
            f'repeatCount="indefinite" values="{scale_vals}"/>'
            f'<circle r=".62" fill="#fff" stroke="#111827" stroke-width=".12"/></g></g>')

    # impact flash at the overhead kick, ripple when the ball hits the net
    cx, cy = CONTACT_P
    flash = (f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="0" fill="#fff" fill-opacity=".25" stroke="#fff" stroke-width=".16">'
             f'<animate attributeName="r" dur="{fmt(T)}s" repeatCount="indefinite" values="0;0;2.1;2.1" '
             f'keyTimes="{k_times(0, CONTACT_T, CONTACT_T + 0.3, T)}"/>'
             f'<animate attributeName="opacity" dur="{fmt(T)}s" repeatCount="indefinite" values="0;0;1;0;0" '
             f'keyTimes="{k_times(0, CONTACT_T - 0.01, CONTACT_T, CONTACT_T + 0.3, T)}"/></circle>')
    gx, gy = 105.6, GOAL_P[1]
    g0, g1 = GOAL_T, GOAL_T + 0.8
    ripple = (f'<circle cx="{gx}" cy="{fmt(gy)}" r="0" fill="none" stroke="#fff" stroke-width=".18">'
              f'<animate attributeName="r" dur="{fmt(T)}s" repeatCount="indefinite" values="0;0;3.4;3.4" '
              f'keyTimes="{k_times(0, g0, g1, T)}"/>'
              f'<animate attributeName="stroke-opacity" dur="{fmt(T)}s" repeatCount="indefinite" '
              f'values="0;0;.9;0;0" keyTimes="{k_times(0, g0 - 0.01, g0, g1, T)}"/></circle>')

    trail = (
        f'<mask id="reveal" maskUnits="userSpaceOnUse" x="-10" y="0" width="130" height="70">'
        f'<path d="{reveal}" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round" '
        f'stroke-dasharray="{fmt(dash)} {fmt(dash)}" stroke-dashoffset="{fmt(offs[0])}">'
        f'<animate attributeName="stroke-dashoffset" dur="{fmt(T)}s" repeatCount="indefinite" '
        f'values="{";".join(fmt(o) for o in offs)}"/></path></mask>'
        f'<g mask="url(#reveal)" fill="none" stroke="#fff" stroke-opacity=".75" stroke-linecap="round">'
        f'<path d="{"".join(solid)}" stroke-width=".2"/>'
        f'<path d="{"".join(dashed)}" stroke-width=".18" stroke-dasharray=".6 .45"/></g>')

    # title plate
    name_d, name_w = text_outline(font_bold, NAME, 62, spacing=5)
    tag_d, tag_w = text_outline(font_regular, TAGLINE, 25, spacing=0.6)
    plate_w = max(name_w, tag_w) + 84
    plate_h = 136
    px, py = (W - plate_w) / 2, (H - plate_h) / 2
    title = (
        f'<rect x="{fmt(px)}" y="{fmt(py)}" width="{fmt(plate_w)}" height="{plate_h}" rx="20" '
        f'fill="#0b2614" fill-opacity=".5" stroke="#fff" stroke-opacity=".16"/>'
        f'<g filter="url(#shadow)" fill="#fff">'
        f'<path transform="translate({fmt((W - name_w) / 2)},{fmt(py + 70)})" d="{name_d}"/>'
        f'<path transform="translate({fmt((W - tag_w) / 2)},{fmt(py + 111)})" d="{tag_d}" fill-opacity=".92"/>'
        f'</g>')
    cap_d, _ = text_outline(font_regular, CAPTION, 17, spacing=0.3)
    caption = (f'<path transform="translate(26,{fmt(H - 22)})" d="{cap_d}" fill="#fff" fill-opacity=".72" '
               f'filter="url(#shadow)"/>')

    tx, ty = -X0 * S, -Y0 * S
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="title desc">
<title id="title">Songyun Jeong, Sports Analytics × Machine Learning</title>
<desc id="desc">A top-down, dot-style recreation of Wayne Rooney's bicycle kick for Manchester United against Manchester City in February 2011.</desc>
<defs>
<clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>
<radialGradient id="vignette" cx="50%" cy="50%" r="72%"><stop offset="55%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity=".38"/></radialGradient>
<filter id="shadow" x="-10%" y="-40%" width="120%" height="180%"><feDropShadow dx="0" dy="2" stdDeviation="2.4" flood-color="#000" flood-opacity=".45"/></filter>
</defs>
<g clip-path="url(#frame)">
<g transform="translate({fmt(tx)},{fmt(ty)}) scale({S:.5f})">
{pitch_svg()}
<g>{fade}
{trail}
{"".join(players)}
{ball}
{flash}
{ripple}
</g>
</g>
<rect width="{W}" height="{H}" fill="url(#vignette)"/>
{title}
{caption}
</g>
</svg>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--out", default="assets/banner.svg")
    ap.add_argument("--font-bold", default="/root/.fonts/Paperlogy-7Bold.ttf")
    ap.add_argument("--font-regular", default="/root/.fonts/Paperlogy-4Regular.ttf")
    args = ap.parse_args()
    svg = build(args.font_bold, args.font_regular)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {args.out} ({len(svg.encode()) / 1024:.1f} KB, {W}x{H})")


if __name__ == "__main__":
    main()
