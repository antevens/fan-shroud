"""Card-clip shroud: a pocketed side wall and bottom plate that ride on TPU grips pushed onto the cards.

Each card gets a soft U-channel grip over its top PCB edge. The ABS wall has a pocket per card
(two ribs and, for shorter cards, a pad) that the grip sits in, so the wall seals to every card
edge. The top card's PCB is the roof of the top channel, so there is no lid; a short stub only
bridges from the duct flange to that card's tail. The bottom plate closes the lowest channel.
"""

from __future__ import annotations

from build123d import Align, Box, Cylinder, Location, Part, chamfer

from duct.outlet import box_between, joint_tie_slots
from duct.params import Params

ON_BASE = (Align.CENTER, Align.CENTER, Align.MIN)


def edge_grip(params: Params, slot: int, length: float | None = None) -> Part:
    """U-channel grip for the card in `slot`, printed back-down with the channel opening up.

    Local frame: X along the card, Y across the PCB (grip width), Z = height (back at Z = 0).
    """
    length = params.grip_length(slot) if length is None else length
    body = Box(length, params.grip_outer_width, params.grip_height(slot), align=ON_BASE)
    slot_cut = Box(length + 2, params.grip_slot_width, params.grip_engagement + 1, align=ON_BASE)
    body -= slot_cut.moved(Location((0, 0, params.grip_back(slot))))
    depth = params.grip_back(slot) - params.tpu_min_wall_thickness
    positions = params.grip_screw_local_x(slot) if length == params.grip_length(slot) else [0.0]
    for x in positions:
        pilot = Cylinder(params.grip_screw_pilot / 2, depth + 1, align=ON_BASE).moved(Location((x, 0, -1)))
        body -= pilot
    return body


def pockets(params: Params) -> Part:
    """Ribs and pads on the wall's inner face forming one pocket per card grip."""
    x0, x1 = params.shroud_x_min, params.shroud_x_max
    y_wall = params.shroud_wall_inner_y
    result: Part | None = None
    for slot in range(params.slot_positions_covered):
        y_reach = params.pocket_inner_y(slot)
        for z0, z1 in params.pocket_rib_z_ranges(slot):
            rib = box_between(x0, x1, y_reach, y_wall + 0.01, z0, z1)
            result = rib if result is None else result + rib
        pad_y = params.pocket_floor_y(slot)
        if y_wall - pad_y > 0.05:
            pz0, pz1 = params.pocket_z_range(slot)
            result += box_between(x0, x1, pad_y, y_wall + 0.01, pz0, pz1)
    assert result is not None
    return result


def end_flange(params: Params) -> Part:
    """Ring at the tail end matching the duct's outlet frame outline."""
    y0, y1, z0, z1 = params.frame_bounds()
    x0 = params.shroud_x_min
    x1 = x0 + params.gasket_lip_thickness
    return box_between(x0, x1, y0, y1, z0, z1) - box_between(
        x0 - 1, x1 + 1, params.outlet_y_min, params.outlet_y_max, params.outlet_z_min, params.outlet_z_max
    )


def card_shroud(params: Params) -> Part:
    x0, x1 = params.shroud_x_min, params.shroud_x_max
    y_in, y_out = params.shroud_wall_inner_y, params.shroud_wall_outer_y
    y_min = params.cover_y_min
    wall = box_between(x0, x1, y_in, y_out, params.shroud_bottom_z, params.shroud_top_z)
    bottom = box_between(x0, x1, y_min, y_out, params.shroud_bottom_z, params.outlet_z_min)
    stub = box_between(x0, params.stub_x_max, y_min, y_out, params.outlet_z_max, params.outlet_z_max + params.wall_thickness)
    fy0, _, fz0, fz1 = params.frame_bounds()
    xg = x0 + params.flange_gusset_length
    gussets = box_between(x0, xg, fy0, y_min + 0.01, params.outlet_z_max, fz1)
    gussets += box_between(x0, xg, fy0, y_min + 0.01, fz0, params.outlet_z_min)
    body = wall + bottom + stub + gussets + end_flange(params) + pockets(params)
    inner = [
        e for e in body.edges()
        if abs(e.center().X - x1) < 1e-6 and (
            (abs(e.center().Y - y_in) < 1e-6 and params.outlet_z_min < e.center().Z < params.outlet_z_max)
            or (abs(e.center().Z - params.outlet_z_min) < 1e-6 and e.center().Y < y_in)
        )
    ]
    if inner and params.cover_edge_chamfer > 0:
        body = chamfer(inner, length=params.cover_edge_chamfer)
    tie_x = params.shroud_x_min + params.gasket_lip_thickness + params.joint_tie_offset
    body -= joint_tie_slots(params, tie_x)
    # Screw clearance holes through the wall into each grip's back, at fixed X positions.
    for slot in range(params.slot_positions_covered):
        for x in params.grip_screw_x:
            hole = Cylinder(params.grip_screw_diameter / 2 + 0.15, params.wall_thickness + 6, rotation=(90, 0, 0))
            body -= hole.moved(Location((x, params.shroud_wall_outer_y - 1, params.pcb_z(slot))))
    return body
