"""Floor tray sealing the card-zone perforations; its upstand carries the duct mount groove."""

from __future__ import annotations

from build123d import Part

from duct.mounts import pin_hole_cutter, pin_points
from duct.outlet import box_between, zip_tie_cutter
from duct.params import Params


def tray_pin_points(params: Params) -> list[tuple[float, float]]:
    x_range = (params.upstand_x_max, params.tray_x_max)
    y_range = (params.tray_y_min, params.tray_y_max)
    return pin_points(params, x_range, y_range, params.pin_count_x, params.pin_count_y, params.tray_edge_margin)


def sheet(params: Params) -> Part:
    return box_between(
        params.tray_x_min, params.tray_x_max,
        params.tray_y_min, params.tray_y_max,
        params.midplate_z, params.tray_top_z,
    )


def rim(params: Params) -> Part:
    """Lip along the three free edges; the side-panel lip also retains the cover's wall."""
    z0, z1 = params.tray_top_z, params.tray_top_z + params.tray_lip_height
    w = params.tray_lip_width
    x0, x1 = params.upstand_x_max, params.tray_x_max
    y0, y1 = params.tray_y_min, params.tray_y_max
    return (
        box_between(x0, x1, y0, y0 + w, z0, z1)
        + box_between(x0, x1, y1 - w, y1, z0, z1)
        + box_between(x1 - w, x1, y0, y1, z0, z1)
    )


def upstand(params: Params) -> Part:
    """Block across the tray's upstream edge with the groove the duct's mount bar drops into."""
    y0, y1 = params.tray_y_min, params.tray_y_max
    block = box_between(
        params.upstand_x_min, params.upstand_x_max, y0, y1, params.tray_top_z, params.groove_floor_z
    )
    fence_z1 = params.fence_top_z
    fences = box_between(params.upstand_x_min, params.groove_x_min, y0, y1, params.groove_floor_z, fence_z1)
    fences += box_between(params.groove_x_max, params.upstand_x_max, y0, y1, params.groove_floor_z, fence_z1)
    bar_y0, bar_y1, _, _ = params.frame_bounds()
    clr = params.mount_groove_clearance
    stops = box_between(params.groove_x_min, params.groove_x_max, y0, bar_y0 - clr, params.groove_floor_z, fence_z1)
    stops += box_between(params.groove_x_min, params.groove_x_max, bar_y1 + clr, y1, params.groove_floor_z, fence_z1)
    return block + fences + stops - zip_tie_cutter(params, params.upstand_x_min, params.upstand_x_max)


def floor_tray(params: Params) -> Part:
    tray = sheet(params) + rim(params)
    if params.mount_style == "case":
        tray += upstand(params)
    holes = pin_hole_cutter(params, tray_pin_points(params), params.midplate_z, params.tray_top_z)
    if holes is not None:
        tray -= holes
    return tray
