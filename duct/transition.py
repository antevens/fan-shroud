"""Lofted body from the fan opening to the card-stack outlet, with per-slot vanes."""

from __future__ import annotations

from build123d import Part, Plane, Polyline, Pos, Rectangle, Sketch, extrude, loft, make_face

from duct.params import Params


def rect_on_yz(x: float, y0: float, y1: float, z0: float, z1: float) -> Sketch:
    """Axis-aligned rectangle in the plane X = x spanning the given Y and Z ranges."""
    return Plane.YZ.offset(x) * Pos((y0 + y1) / 2, (z0 + z1) / 2) * Rectangle(y1 - y0, z1 - z0)


def cavity(params: Params) -> Part:
    """Air passage from the flange's inner face to the outlet plane."""
    fan_end = rect_on_yz(
        params.fan_inner_x,
        params.fan_inner_y_min, params.fan_inner_y_max,
        params.fan_inner_z_min, params.fan_inner_z_max,
    )
    outlet_end = rect_on_yz(
        params.outlet_x,
        params.outlet_y_min, params.outlet_y_max,
        params.outlet_z_min, params.outlet_z_max,
    )
    return loft([fan_end, outlet_end], ruled=True)


def outer_body(params: Params) -> Part:
    """Cavity grown by the wall thickness, measured perpendicular to each tilted wall."""
    oy0 = params.wall_normal_offset("y_min")
    oy1 = params.wall_normal_offset("y_max")
    oz0 = params.wall_normal_offset("z_min")
    oz1 = params.wall_normal_offset("z_max")
    fan_end = rect_on_yz(
        params.fan_inner_x,
        params.fan_inner_y_min - oy0, params.fan_inner_y_max + oy1,
        params.fan_inner_z_min - oz0, params.fan_inner_z_max + oz1,
    )
    outlet_end = rect_on_yz(
        params.outlet_x,
        params.outlet_y_min - oy0, params.outlet_y_max + oy1,
        params.outlet_z_min - oz0, params.outlet_z_max + oz1,
    )
    return loft([fan_end, outlet_end], ruled=True)


def vane_planes(params: Params) -> list[tuple[float, float]]:
    """(z at the fan end, z at the outlet) for each internal vane.

    The fan opening is split into equal parts; the outlet follows the slot pitch.
    """
    n = params.slot_positions_covered
    planes = []
    for k in range(1, n):
        z_fan = params.fan_inner_z_min + k * params.fan_inner / n
        z_out = params.outlet_z_min + k * params.slot_pitch
        planes.append((z_fan, z_out))
    return planes


def vanes(params: Params, passage: Part) -> Part | None:
    """Splitter vanes trimmed to the passage; None when there is a single channel."""
    planes = vane_planes(params)
    if not planes:
        return None
    margin = params.wall_thickness * 2
    x_fan = params.fan_inner_x - margin
    x_out = params.outlet_x + margin
    result: Part | None = None
    for z_fan, z_out in planes:
        # Extend past both ends so the end caps clear the cavity faces before trimming.
        slope = (z_out - z_fan) / params.transition_length_eff
        outline = Polyline(
            (x_fan, params.fan_inner_y_min - margin, z_fan - slope * margin),
            (x_fan, params.fan_inner_y_max + margin, z_fan - slope * margin),
            (x_out, params.outlet_y_max + margin, z_out + slope * margin),
            (x_out, params.outlet_y_min - margin, z_out + slope * margin),
            close=True,
        )
        slab = extrude(make_face(outline), amount=params.vane_thickness / 2, both=True)
        trimmed = slab & passage
        result = trimmed if result is None else result + trimmed
    return result


def shell(params: Params) -> Part:
    """Walls of the transition: outer body minus the cavity."""
    return outer_body(params) - cavity(params)
