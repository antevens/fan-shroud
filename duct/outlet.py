"""Outlet gasket frame and the mount bar that drops into the tray groove."""

from __future__ import annotations

from build123d import Align, Box, Location, Part

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
    return ring
