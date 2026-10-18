"""Card-clip shroud: a pocketed side wall and bottom plate that ride on TPU grips pushed onto the cards.

Each card gets a soft U-channel grip over its top PCB edge. The ABS wall has a pocket per card
(two ribs and, for shorter cards, a pad) that the grip sits in, so the wall seals to every card
edge. The top card's PCB is the roof of the top channel, so there is no lid; a short stub only
bridges from the tail end wall to that card's tail. The bottom plate closes the lowest channel.
A 60 mm fan bolts straight onto the tail end wall with standard fan screws driven from inside (reached
from the open motherboard side before the shroud goes on). At the bracket end one rib per card runs
along the wall to its edge and angles up to an ear on that card's PCI bracket tab, under its screw.
The shroud prints standing on its tail end wall, so the pocket ribs and arms stand vertical.
"""

from __future__ import annotations

from build123d import Align, Box, Cylinder, Location, Part, Plane, Polyline, chamfer, extrude, make_face

from duct.outlet import box_between
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


def edge_grip_bodies(params: Params, slot: int, length: float | None = None) -> dict[str, Part]:
    """The grip split at the lip root: 'back' prints in the firm TPU, 'lips' in the soft one."""
    grip = edge_grip(params, slot, length)
    length = (length if length is not None else params.grip_length(slot)) + 2
    width = params.grip_outer_width + 2
    back_zone = Box(length, width, params.grip_back(slot), align=ON_BASE)
    lips_zone = Box(length, width, params.grip_engagement + 1, align=ON_BASE).moved(Location((0, 0, params.grip_back(slot))))
    return {"back": grip & back_zone, "lips": grip & lips_zone}


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


def tail_end_wall(params: Params) -> Part:
    """Plate across the shroud's tail with the fan opening and four fan screw clearance holes."""
    x0 = params.shroud_x_min
    x1 = x0 + params.tail_wall_thickness
    y0, y1 = params.tail_wall_y_range
    z0, z1 = params.tail_wall_z_range
    wall = box_between(x0, x1, y0, y1, z0, z1)
    along_x = (0, 90, 0)
    cy, cz = params.tail_fan_center_y_eff, params.tail_fan_center_z_eff
    length = params.tail_wall_thickness + 2
    wall -= Cylinder(params.tail_fan_opening / 2, length, rotation=along_x).moved(Location(((x0 + x1) / 2, cy, cz)))
    for y, z in params.tail_fan_hole_points():
        wall -= Cylinder(params.fan_screw_clearance / 2, length, rotation=along_x).moved(Location(((x0 + x1) / 2, y, z)))
    return wall


def bracket_mount(params: Params) -> Part:
    """One rib per covered slot: along the wall's outer face to the shroud's bracket-end edge, then angled
    up to an ear under that card's bracket screw, so the screws hold the cards and the shroud together.

    The ribs stand on the outside of the wall (outside the card zone), so the exhaust gap stays open between
    them and the space under each ear stays free for the metal bracket tab.
    """
    arm_face = make_face(Polyline(*params.bracket_arm_outline(), close=True))
    width = params.bracket_arm_width
    y_mid = params.bracket_tab_y + params.bracket_tab_thickness / 2
    result: Part | None = None
    for z in params.bracket_screw_points():
        arm = extrude(Plane.XY.offset(z - width / 2) * arm_face, amount=width)
        hole = Cylinder(params.bracket_screw_clearance / 2, params.bracket_tab_thickness + 2, rotation=(90, 0, 0))
        arm -= hole.moved(Location((params.bracket_screw_x, y_mid, z)))
        result = arm if result is None else result + arm
    assert result is not None
    return result


def card_shroud(params: Params) -> Part:
    x0, x1 = params.shroud_x_min, params.shroud_x_max
    y_in, y_out = params.shroud_wall_inner_y, params.shroud_wall_outer_y
    y_min = params.cover_y_min
    wall = box_between(x0, x1, y_in, y_out, params.shroud_bottom_z, params.shroud_top_z)
    bottom = box_between(x0, x1, y_min, y_out, params.shroud_bottom_z, params.outlet_z_min)
    stub = box_between(x0, params.stub_x_max, y_min, y_out, params.outlet_z_max, params.outlet_z_max + params.wall_thickness)
    body = wall + bottom + stub + tail_end_wall(params) + pockets(params)
    inner = [
        e for e in body.edges()
        if abs(e.center().X - x1) < 1e-6 and (
            (abs(e.center().Y - y_in) < 1e-6 and params.outlet_z_min < e.center().Z < params.outlet_z_max)
            or (abs(e.center().Z - params.outlet_z_min) < 1e-6 and e.center().Y < y_in)
        )
    ]
    if inner and params.cover_edge_chamfer > 0:
        body = chamfer(inner, length=params.cover_edge_chamfer)
    # Screw clearance holes through the wall into each grip's back, at fixed X positions.
    for slot in range(params.slot_positions_covered):
        for x in params.grip_screw_x:
            hole = Cylinder(params.grip_screw_diameter / 2 + 0.15, params.wall_thickness + 6, rotation=(90, 0, 0))
            body -= hole.moved(Location((x, params.shroud_wall_outer_y - 1, params.pcb_z(slot))))
    return body + bracket_mount(params)
