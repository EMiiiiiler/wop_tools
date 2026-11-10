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
