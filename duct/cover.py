"""Passive side cover: a lid under the GPU and a wall along the card top edges.

Together with the tray, the motherboard and the duct outlet it closes the slot area so the
air has to travel along the cards to the exhaust gap. The optional 120 mm booster fan would
cut into this wall.
"""

from __future__ import annotations

from build123d import Axis, Part, chamfer

from duct.outlet import box_between
from duct.params import Params


def side_cover(params: Params) -> Part:
    x0, x1 = params.cover_x_min, params.cover_x_max
    y_in, y_out = params.cover_y_inner, params.cover_y_outer
    lid = box_between(x0, x1, params.cover_y_min, y_out, params.cover_lid_bottom_z, params.cover_lid_top_z)
    wall = box_between(x0, x1, y_in, y_out, params.tray_top_z, params.cover_lid_top_z)
    cover = lid + wall
    # Round the exhaust-end inner edges so the air turns out smoothly.
    downstream = cover.edges().filter_by(lambda e: abs(e.center().X - x1) < 1e-6)
    inner = downstream.filter_by(
        lambda e: (e.center().Z < params.cover_lid_bottom_z + 1e-6 and e.center().Y < y_in + 1e-6)
        or (e.center().Y < y_in + 1e-6 and e.center().Z < params.cover_lid_bottom_z + 1e-6)
    )
    inner = [e for e in downstream if (abs(e.center().Z - params.cover_lid_bottom_z) < 1e-6 and e.center().Y < y_in)
             or (abs(e.center().Y - y_in) < 1e-6 and e.center().Z < params.cover_lid_bottom_z)]
    if inner and params.cover_edge_chamfer > 0:
        cover = chamfer(inner, length=params.cover_edge_chamfer)
    return cover
