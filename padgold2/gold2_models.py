"""Gold Rush Gulch: Flood Day - the few models the reimagined layout adds to padgold/gold_models.py"""
import math
import numpy as np
from woplib import models as ML
from meshlib import revolve, rbox, tube
import gold_models as GM

M_ = GM.M_


def lift_frame(w=128, h=520):
    """mine-cage head frame standing in front of a cliff: two posts on the open side, a cap beam running back over the
    shaft, a sheave wheel and the hoist rope (local: shaft centred on the origin, cliff on -x)"""
    X = ML.Model(); t = M_(X, 'timber'); ir = M_(X, 'iron')
    p = w / 2 + 12
    for sy in (-p, p):
        rbox(t, (p - 8, sy - 8, 0), (p + 8, sy + 8, h), r=1, k=1, tile=64)
        rbox(t, (-p - 60, sy - 7, h - 14), (p + 20, sy + 7, h), r=1, k=1, tile=64)
        tube(ir, [(p, sy, h * 0.55), (-p - 40, sy, h - 10)], 3, nseg=6)
    rbox(t, (p - 8, -p - 16, h), (p + 8, p + 16, h + 14), r=1, k=1, tile=64)
    R = 44
    P = [(R * math.cos(a), 0, h + 30 + R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)]
    tube(ir, P, 4, nseg=6, caps=(False, False))
    for k in range(6):
        a = 2 * math.pi * k / 6
        tube(ir, [(0, 0, h + 30), (R * math.cos(a), 0, h + 30 + R * math.sin(a))], 2.5, nseg=5)
    tube(ir, [(0, -p - 10, h + 30), (0, p + 10, h + 30)], 5, nseg=8)
    return X


def pan_rim(r=300):
    """rolled iron rim of the giant gold pan, lying on the sand round the octagonal pool"""
    X = ML.Model(); ir = M_(X, 'iron')
    revolve(ir, [(r + 72, 0), (r + 68, 8), (r + 44, 12), (r + 31, 8), (r + 27, 0)], n=48, u_tiles=12)
    return X


def tram_bents(tram, ztop):
    """timber bents under the tramway ramp (world coordinates; the model is placed at the origin)"""
    x0, y0, x1, y1 = tram
    X = ML.Model(); t = M_(X, 'timber'); ir = M_(X, 'iron')
    for y in np.arange(y0 + 120, y1 - 60, 180):
        zt = ztop
        for x in (x0 + 14, x1 - 14):
            rbox(t, (x - 7, y - 7, 0), (x + 7, y + 7, zt), r=1, k=1, tile=64)
        tube(ir, [(x0 + 14, y, 30), (x1 - 14, y, zt - 30)], 3, nseg=6)
        tube(ir, [(x1 - 14, y, 30), (x0 + 14, y, zt - 30)], 3, nseg=6)
    return X


def _ring_xz(M, cx, y, cz, R, r, spokes=4, hub=4):
    """hand wheel standing in the x-z plane (faces +-y): rim tube, spokes, hub"""
    P = [(cx + R * math.cos(a), y, cz + R * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)]
    tube(M, P, r, nseg=6, caps=(False, False))
    for k in range(spokes):
        a = 2 * math.pi * k / spokes
        tube(M, [(cx, y, cz), (cx + R * math.cos(a), y, cz + R * math.sin(a))], r * 0.6, nseg=5)
    tube(M, [(cx, y - hub, cz), (cx, y + hub, cz)], r * 1.6, nseg=8)


def _ring_xy(M, cx, cy, z, R, r, spokes=4):
    """hand wheel lying flat (faces +-z)"""
    P = [(cx + R * math.cos(a), cy + R * math.sin(a), z) for a in np.linspace(0, 2 * math.pi, 25)]
    tube(M, P, r, nseg=6, caps=(False, False))
    for k in range(spokes):
        a = 2 * math.pi * k / spokes
        tube(M, [(cx, cy, z), (cx + R * math.cos(a), cy + R * math.sin(a), z)], r * 0.6, nseg=5)


def dam_valve(h=520):
    """penstock outlet on the dam face (local: face at y = 0, model on -y): pipe out of the wall into a valve chest on
    the ground with a flat hand wheel, a riser pipe up the face with brackets and a second wheel half way up"""
    X = ML.Model(); ir = M_(X, 'iron'); rd = M_(X, 'red'); br = M_(X, 'brass')
    rbox(ir, (-40, -150, 0), (40, -70, 64), r=4, k=2, tile=64)                         # valve chest
    rbox(ir, (-46, -156, 0), (46, -64, 10), r=2, k=1, tile=64)                         # its plinth
    tube(ir, [(0, 0, 92), (0, -90, 92), (0, -108, 84), (0, -110, 64)], 16, nseg=10, caps=(False, False))
    for y in (-4, -86):
        tube(ir, [(0, y - 3, 92), (0, y + 3, 92)], 22, nseg=10)                        # flanges
    tube(br, [(0, -110, 64), (0, -110, 96)], 3, nseg=6)
    _ring_xy(rd, 0, -110, 96, 30, 3.5)
    tube(ir, [(0, -18, 92), (0, -18, h)], 12, nseg=10, caps=(False, True))             # riser up the face
    for z in np.arange(160, h, 120):
        rbox(ir, (-20, -32, z - 6), (20, 0, z + 6), r=1, k=1, tile=64)                 # wall brackets
    _ring_xz(rd, 0, -36, 300, 26, 3)
    tube(br, [(0, -18, 300), (0, -36, 300)], 3, nseg=6)
    return X


def sluice_gate(span=236, h=300, leaf=(170, 262)):
    """steel sluice gate frame at the head of the spillway, gate leaf winched up out of the way (local: crest edge
    at y = 0, posts on +y, slide on -y)"""
    X = ML.Model(); ir = M_(X, 'iron'); w = M_(X, 'wood_d'); rd = M_(X, 'red')
    for s in (-1, 1):
        rbox(ir, (s * span - 10, 4, 0), (s * span + 10, 28, h), r=1, k=1, tile=64)
        rbox(ir, (s * span - 16, 0, 0), (s * span + 16, 32, 12), r=1, k=1, tile=64)    # base plate
        tube(ir, [(s * span, 30, h * 0.35), (s * (span - 70), 16, h - 12)], 3, nseg=6)  # knee brace
    rbox(ir, (-span - 12, 2, h - 20), (span + 12, 30, h), r=1, k=1, tile=64)           # cross beam
    rbox(w, (-span + 12, 10, leaf[0]), (span - 12, 22, leaf[1]), r=1, k=1, tile=64)     # the leaf (planked)
    for z in (leaf[0] + 8, leaf[1] - 8):
        rbox(ir, (-span + 12, 8, z - 4), (span - 12, 24, z + 4), r=1, k=1, tile=64)
    for x in (-120, 120):
        tube(ir, [(x, 16, leaf[1]), (x, 16, h - 20)], 1.6, nseg=4)                     # chains
        tube(ir, [(x, 16, h + 12), (x, 16, h)], 4, nseg=6)
    tube(ir, [(-150, 16, h + 16), (150, 16, h + 16)], 9, nseg=10)                      # winch drum
    _ring_xz(rd, 170, 16, h + 16, 30, 3)
    _ring_xz(rd, -170, 16, h + 16, 30, 3)
    for x in (-160, 160):
        rbox(ir, (x - 5, 10, h), (x + 5, 22, h + 26), r=1, k=1, tile=64)
    return X


def deck_gear():
    """aft deck of the steamer: capstan (origin), two bollards and a coil of rope (local)"""
    X = ML.Model(); ir = M_(X, 'iron'); w = M_(X, 'wood_d'); bk = M_(X, 'black'); cv = M_(X, 'canvas')
    revolve(w, [(26, 0), (26, 6), (18, 10), (16, 40), (22, 46), (22, 54), (0.1, 58)], n=16)
    for k in range(6):
        a = 2 * math.pi * k / 6
        tube(w, [(18 * math.cos(a), 18 * math.sin(a), 48), (58 * math.cos(a), 58 * math.sin(a), 50)], 2.5, nseg=5)
    for (bx, by) in ((170, -50), (170, 40)):
        revolve(bk, [(11, 0), (9, 22), (14, 26), (14, 30), (0.1, 32)], n=12, cx=bx, cy=by)
    for i in range(4):
        rr = 22 - 4 * i
        P = [(90 + rr * math.cos(a), 20 + rr * math.sin(a), 4 + 2 * i) for a in np.linspace(0, 2 * math.pi, 17)]
        tube(cv, P, 4, nseg=6, caps=(False, False))
    revolve(cv, [(26, 0), (26, 2), (0.1, 2)], n=12, cx=90, cy=20)
    return X
