"""Small test prints: fan flange, outlet corner, and a pin sizing strip."""

from __future__ import annotations

from build123d import Align, Box, Cylinder, Location, Part, chamfer

from duct.fan import fan_flange_coupon
from duct.outlet import box_between
from duct.params import Params

PIN_STEPS = 5
PIN_STEP = 0.1
PIN_SPACING = 10.0


def outlet_corner_coupon(params: Params, duct: Part, size: float = 25.0, depth: float = 10.0) -> Part:
    """Bottom motherboard-side corner of the outlet end, including the mount bar end."""
    y0, _, z0, _ = params.frame_bounds()
    window = box_between(
        params.outlet_x - depth, params.outlet_x + 1,
        y0 - 1, y0 + size,
        params.mount_bar_bottom_z - 1, z0 + size,
    )
    return duct & window


def pin_sizing_coupon(params: Params) -> Part:
    """Strip with PIN_STEPS pins whose shafts shrink by PIN_STEP each; k notches = k steps.

    The first pin equals the perforation size; pick the smallest step that presses in by hand
    and set peg_clearance to that step.
    """
    length = PIN_SPACING * PIN_STEPS
    width = params.pin_head_diameter + 6
    strip = Box(length, width, params.pin_head_thickness, align=(Align.MIN, Align.CENTER, Align.MIN))
    for k in range(PIN_STEPS):
        x = PIN_SPACING * (k + 0.5)
        step = k * PIN_STEP
        if params.hole_pattern == "slots":
            shaft = Box(params.slot_length - step, params.slot_width - step, params.pin_shaft_length,
                        align=(Align.CENTER, Align.CENTER, Align.MIN))
            tip = min(0.5, (params.slot_width - step) / 4)
        else:
            diameter = params.hole_diameter - step
            shaft = Cylinder(diameter / 2, params.pin_shaft_length, align=(Align.CENTER, Align.CENTER, Align.MIN))
            tip = min(0.5, diameter / 4)
        shaft = chamfer(shaft.faces().sort_by()[-1].edges(), length=tip)
        strip += shaft.moved(Location((x, 0, params.pin_head_thickness)))
        for notch in range(k):
            cut = Box(1.0, 1.5, params.pin_head_thickness + 2, align=(Align.CENTER, Align.MAX, Align.CENTER))
            strip -= cut.moved(Location((x - PIN_SPACING / 2 + 2 + notch * 2, width / 2, params.pin_head_thickness / 2)))
    return strip


GRIP_COUPON_LENGTH = 30.0


def grip_coupon(params: Params) -> Part:
    """Short grip to test the squeeze on a spare PCB edge and the fit in the pocket coupon."""
    from duct.shroud import edge_grip

    return edge_grip(params, params.slot_positions_covered - 1, length=GRIP_COUPON_LENGTH)


def pocket_coupon(params: Params, shroud: Part) -> Part:
    """Slice of the shroud wall holding the top card's pocket, to test the grip fit."""
    slot = params.slot_positions_covered - 1
    z0, z1 = params.pocket_z_range(slot)
    x_mid = params.grip_screw_x[0]
    window = box_between(
        x_mid - GRIP_COUPON_LENGTH / 2 - 3, x_mid + GRIP_COUPON_LENGTH / 2 + 3,
        params.pocket_inner_y(slot) - 1, params.shroud_wall_outer_y + 1,
        z0 - 2 * params.pocket_rib - 2, z1 + 2 * params.pocket_rib + 2,
    )
    return shroud & window


def coupon_parts(params: Params, parts: dict[str, Part]) -> dict[str, Part]:
    coupons = {
        "coupon_fan_flange": fan_flange_coupon(params),
        "coupon_outlet_corner": outlet_corner_coupon(params, parts["duct"]),
    }
    if params.mount_style == "card_clip":
        coupons["coupon_grip"] = grip_coupon(params)
        coupons["coupon_pocket"] = pocket_coupon(params, parts["shroud"])
    else:
        coupons["coupon_pin_sizing"] = pin_sizing_coupon(params)
    return coupons
