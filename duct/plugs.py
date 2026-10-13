"""Blanking plug that closes one outlet channel."""

from __future__ import annotations

import math

from build123d import Align, Box, Location, Part, Plane, Rectangle, loft

from duct.params import Params

ON_BASE = (Align.CENTER, Align.CENTER, Align.MIN)


def channel_opening(params: Params) -> tuple[float, float]:
    """(width along Y, height along Z) of the smallest channel at the outlet face, so one plug fits all."""
    bounds = params.channel_boundaries_z
    smallest = min(b1 - b0 for b0, b1 in zip(bounds, bounds[1:]))
    return params.card_zone_height, smallest - params.vane_thickness


def blanking_plug(params: Params) -> Part:
    """Wedge that enters the channel, a plate that stops on the vanes, and a pull handle.

    Modelled in print orientation: wedge narrow end on Z = 0, plate at Z = plug_depth, handle on top.
    Local X spans the channel width (duct Y), local Y the channel height (duct Z). The wedge only
    tapers where the duct walls expand toward the outlet; contracting walls leave it straight.
    """
    width, height = channel_opening(params)
    clearance = params.plug_clearance
    depth = params.plug_depth
    thick = params.plug_plate_thickness
    tilts = params.side_tilt_angles()
    shrink_y = depth * math.tan(math.radians(max(0.0, tilts["y_min"], tilts["y_max"])))
    shrink_z = depth * math.tan(math.radians(max(0.0, tilts["z_min"], tilts["z_max"])))
    narrow = Plane.XY * Rectangle(width - 2 * clearance - 2 * shrink_y, height - 2 * clearance - 2 * shrink_z)
    wide = Plane.XY.offset(depth) * Rectangle(width - 2 * clearance, height - 2 * clearance)
    wedge = loft([narrow, wide], ruled=True)
    plate = Box(width - 2 * clearance, params.slot_pitch - 0.2, thick, align=ON_BASE).moved(Location((0, 0, depth)))
    handle = Box(
        params.plug_handle_length, params.plug_handle_thickness, params.plug_handle_height, align=ON_BASE
    ).moved(Location((0, 0, depth + thick)))
    return wedge + plate + handle
