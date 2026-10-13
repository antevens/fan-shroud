"""Outlet gasket frame and the mount bar that drops into the tray groove."""

from __future__ import annotations

from build123d import Align, Box, Cylinder, Location, Part

from duct.params import Params

CENTERED = (Align.CENTER, Align.CENTER, Align.CENTER)


def box_between(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Part:
    """Axis-aligned box spanning the given ranges."""
    return Box(x1 - x0, y1 - y0, z1 - z0, align=CENTERED).moved(
        Location(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    )


def zip_tie_centers_y(params: Params) -> list[float]:
    """Y centres of the zip-tie slot pairs along the mount bar."""
    y0, y1, _, _ = params.frame_bounds()
    span = y1 - y0
    half = params.zip_tie_pair_spacing / 2
    return [y0 + span * 0.25 - half, y0 + span * 0.25 + half, y0 + span * 0.75 - half, y0 + span * 0.75 + half]


def zip_tie_cutter(params: Params, x0: float, x1: float) -> Part:
    """Slots through X at the shared zip-tie positions, spanning x0..x1."""
    cutter: Part | None = None
    for y in zip_tie_centers_y(params):
        slot = box_between(
            x0 - 1, x1 + 1,
            y - params.zip_tie_slot_width / 2, y + params.zip_tie_slot_width / 2,
            params.zip_tie_z - params.zip_tie_slot_height / 2, params.zip_tie_z + params.zip_tie_slot_height / 2,
        )
        cutter = slot if cutter is None else cutter + slot
    assert cutter is not None
    return cutter


def joint_ears(params: Params, x0: float, x1: float) -> Part:
    """Screw bars along the bottom edge and the side-panel edge of the outlet frame outline.

    Continuous bars rather than separate ears: both parts print with this face on the bed, so a bar
    is just more first-layer footprint, while ears off the frame would be cantilevers.
    """
    y0, y1, z0, z1 = params.frame_bounds()
    bottom = box_between(x0, x1, y0, params.joint_side_y_outer, params.joint_ear_z_bottom, params.joint_ear_z_top + 0.01)
    side = box_between(x0, x1, y1 - 0.01, params.joint_side_y_outer, params.joint_ear_z_bottom, z1)
    return bottom + side


def joint_screw_points(params: Params) -> list[tuple[float, float]]:
    """(y, z) of every joint screw: along the bottom bar and up the side bar."""
    points = [(y, params.joint_screw_z) for y in params.joint_ear_y()]
    points += [(params.joint_side_screw_y, z) for z in params.joint_side_screw_z()]
    return points


def joint_hole_cutter(params: Params, diameter: float, x0: float, x1: float) -> Part:
    """Holes along X through the screw bars."""
    result: Part | None = None
    for y, z in joint_screw_points(params):
        hole = Cylinder(diameter / 2, x1 - x0 + 2, rotation=(0, 90, 0)).moved(Location(((x0 + x1) / 2, y, z)))
        result = hole if result is None else result + hole
    assert result is not None
    return result


def outlet_frame(params: Params) -> Part:
    """Gasket lip frame at the outlet face plus, for the case mount, the mount bar below it."""
    y0, y1, z0, z1 = params.frame_bounds()
    x1 = params.outlet_x
    x0 = x1 - params.gasket_lip_thickness
    frame = box_between(x0, x1, y0, y1, z0, z1) - box_between(
        x0 - 1, x1 + 1,
        params.outlet_y_min, params.outlet_y_max,
        params.outlet_z_min, params.outlet_z_max,
    )
    if params.has_mount_bar:
        bar = box_between(x0, x1, y0, y1, params.mount_bar_bottom_z, z0 + 0.01)
        frame = frame + bar - zip_tie_cutter(params, x0, x1)
    if params.mount_style == "card_clip":
        # Thick ears under the outlet frame take self-tapping fan screws driven from the shroud side.
        ear_x0 = x1 - params.joint_ear_thickness
        frame = frame + joint_ears(params, ear_x0, x1) - joint_hole_cutter(params, params.joint_screw_pilot, ear_x0, x1)
    return frame


def outlet_gasket(params: Params) -> Part:
    """Soft frame on the outlet face covering the wall and lip; it touches the card tails."""
    y0, y1, z0, z1 = params.frame_bounds()
    x0 = params.outlet_x
    x1 = x0 + params.outlet_gasket_thickness
    ring = box_between(x0, x1, y0, y1, z0, z1) - box_between(
        x0 - 1, x1 + 1,
        params.outlet_y_min, params.outlet_y_max,
        params.outlet_z_min, params.outlet_z_max,
    )
    if params.mount_style == "card_clip":
        ring = ring + joint_ears(params, x0, x1) - joint_hole_cutter(params, params.joint_screw_clearance + 0.2, x0, x1)
    return ring
