"""Case mount pieces: perforation grid, press-in pins or slot pegs, and the foot under the fan."""

from __future__ import annotations

import math

from build123d import Align, Box, Cylinder, Location, Part, Plane, Polyline, chamfer, extrude, make_face

from duct.outlet import box_between
from duct.params import Params

ON_BASE = (Align.CENTER, Align.CENTER, Align.MIN)
HEAD_MARGIN = 1.5


def grid_point(params: Params, column: int, row: int) -> tuple[float, float]:
    """Centre of the perforation at integer grid indices (column along X, row along Y)."""
    x = params.perforation_origin_x + column * params.hole_pitch
    if params.staggered and row % 2:
        x += params.hole_pitch / 2
    y = params.perforation_origin_y + row * params.hole_row_pitch
    return x, y


def grid_points_within(
    params: Params, x_range: tuple[float, float], y_range: tuple[float, float]
) -> list[tuple[float, float]]:
    """Every perforation centre inside the ranges and clear of the cutouts."""
    x0, x1 = x_range
    y0, y1 = y_range
    row0 = math.floor((y0 - params.perforation_origin_y) / params.hole_row_pitch) - 1
    row1 = math.ceil((y1 - params.perforation_origin_y) / params.hole_row_pitch) + 1
    col0 = math.floor((x0 - params.perforation_origin_x) / params.hole_pitch) - 2
    col1 = math.ceil((x1 - params.perforation_origin_x) / params.hole_pitch) + 1
    half = params.tray_edge_margin
    points = []
    for row in range(row0, row1 + 1):
        for col in range(col0, col1 + 1):
            x, y = grid_point(params, col, row)
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                continue
            if params.overlaps_cutout(x - half, x + half, y - half, y + half):
                continue
            points.append((x, y))
    return points


def nearest_grid_point(params: Params, x: float, y: float) -> tuple[float, float]:
    """Perforation centre closest to (x, y)."""
    span = params.hole_pitch + params.hole_row_pitch
    candidates = grid_points_within(params, (x - span, x + span), (y - span, y + span))
    if not candidates:
        row = round((y - params.perforation_origin_y) / params.hole_row_pitch)
        col = round((x - params.perforation_origin_x) / params.hole_pitch)
        return grid_point(params, col, row)
    return min(candidates, key=lambda c: math.dist(c, (x, y)))


def pin_points(
    params: Params,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    count_x: int,
    count_y: int,
    margin: float,
) -> list[tuple[float, float]]:
    """Perforation centres nearest an evenly spread count_x by count_y pattern inside the margins."""
    x0, x1 = x_range[0] + margin, x_range[1] - margin
    y0, y1 = y_range[0] + margin, y_range[1] - margin
    candidates = grid_points_within(params, (x0, x1), (y0, y1))
    if not candidates:
        return []
    xs = [x0 + (x1 - x0) * i / (count_x - 1) if count_x > 1 else (x0 + x1) / 2 for i in range(count_x)]
    ys = [y0 + (y1 - y0) * j / (count_y - 1) if count_y > 1 else (y0 + y1) / 2 for j in range(count_y)]
    points: list[tuple[float, float]] = []
    for x in xs:
        for y in ys:
            best = min(candidates, key=lambda c: math.dist(c, (x, y)))
            if best not in points:
                points.append(best)
    return points


def pin_shaft(params: Params, length: float, oversize: float = 0.0) -> Part:
    """Shaft matching the perforation: a box for slots, a cylinder for round holes."""
    if params.hole_pattern == "slots":
        return Box(params.peg_x + oversize, params.peg_y + oversize, length, align=ON_BASE)
    return Cylinder((params.pin_diameter + oversize) / 2, length, align=ON_BASE)


def pin(params: Params) -> Part:
    """Press-in pin: head on the bed, shaft up. Shaft is a slip fit in the perforation."""
    if params.hole_pattern == "slots":
        head = Box(params.peg_x + 2 * HEAD_MARGIN, params.peg_y + 2 * HEAD_MARGIN, params.pin_head_thickness, align=ON_BASE)
    else:
        head = Cylinder(params.pin_head_diameter / 2, params.pin_head_thickness, align=ON_BASE)
    shaft = pin_shaft(params, params.pin_shaft_length).moved(Location((0, 0, params.pin_head_thickness)))
    smallest = params.peg_y if params.hole_pattern == "slots" else params.pin_diameter
    tip = min(0.5, smallest / 4)
    shaft = chamfer(shaft.faces().sort_by()[-1].edges(), length=tip)
    return head + shaft


def pin_head_footprint(params: Params) -> tuple[float, float]:
    """(x, y) size of the pin head."""
    if params.hole_pattern == "slots":
        return params.peg_x + 2 * HEAD_MARGIN, params.peg_y + 2 * HEAD_MARGIN
    return params.pin_head_diameter, params.pin_head_diameter


def pin_hole_cutter(params: Params, points: list[tuple[float, float]], z0: float, z1: float) -> Part | None:
    """Vertical through-holes for pins at the given (x, y) centres spanning z0..z1."""
    cutter: Part | None = None
    for x, y in points:
        hole = pin_shaft(params, (z1 - z0) + 2, oversize=params.pin_hole_clearance).moved(Location((x, y, z0 - 1)))
        cutter = hole if cutter is None else cutter + hole
    return cutter


def foot_pin_points(params: Params) -> list[tuple[float, float]]:
    y0 = params.fan_center_y_eff - params.fan_flange_size / 2
    y1 = params.fan_center_y_eff + params.fan_flange_size / 2
    return pin_points(
        params, (params.foot_x_min, params.foot_flat_x_max), (y0, y1), 1, params.foot_pin_count,
        params.tray_edge_margin,
    )


def fan_foot(params: Params) -> Part:
    """Block under the fan end resting on the midplate, with counterbored pin holes.

    Its duct-side face continues the flange's chamfer so it prints outlet-face-down
    without support; under the fan frame it stays foot_overlap below the flange bottom.
    """
    y0 = params.fan_center_y_eff - params.fan_flange_size / 2
    y1 = params.fan_center_y_eff + params.fan_flange_size / 2
    x0, x1 = params.foot_x_min, params.foot_x_max
    z0 = params.midplate_z
    foot = box_between(x0, x1, y0, y1, z0, params.foot_rim_top_z)
    foot -= box_between(x0 - 1, params.fan_face_x, y0 - 1, y1 + 1, params.foot_top_z, params.foot_rim_top_z + 1)
    rise = params.foot_rim_top_z - z0
    ramp = Polyline(
        (x1 + 1, params.foot_rim_top_z + 1, 0),
        (x1 + 1, z0 - 1, 0),
        (x1 - rise - 2, z0 - 1, 0),
        close=True,
    )
    wedge = extrude(make_face(Plane.XZ * ramp), amount=(y1 - y0) / 2 + 1, both=True)
    foot -= wedge.moved(Location((0, (y0 + y1) / 2, 0)))
    points = foot_pin_points(params)
    holes = pin_hole_cutter(params, points, z0, params.foot_top_z)
    if holes is not None:
        foot -= holes
    bore_depth = params.foot_height - params.tray_thickness
    hx, hy = pin_head_footprint(params)
    for x, y in points:
        bore = Box(hx + 0.4, hy + 0.4, bore_depth + 1, align=ON_BASE)
        foot -= bore.moved(Location((x, y, params.foot_top_z - bore_depth)))
    return foot
