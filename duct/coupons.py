"""Small test prints: tail fan mount, grip and pocket (card-clip); fan flange, outlet corner, pin strip (case)."""

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
# Wall kept beside the groove so the standing pocket coupon has a wide enough footprint.
POCKET_COUPON_WALL = 8.0


def coupon_slot(params: Params) -> int:
    """Covered slot the grip and pocket coupons are built for: the middle one, with wall on both sides."""
    return params.slot_positions_covered // 2


def grip_coupon(params: Params) -> Part:
    """Short grip to test the squeeze on a spare PCB edge and the fit in the pocket coupon."""
    from duct.shroud import edge_grip

    return edge_grip(params, coupon_slot(params), length=GRIP_COUPON_LENGTH)


def pocket_coupon(params: Params, shroud: Part) -> Part:
    """Slice of the shroud wall holding one dovetail groove, open at both ends, to test the grip fit."""
    slot = coupon_slot(params)
    g0, g1 = params.pocket_groove_z_range(slot)
    # Centred on that card's grip, clear of the tail end wall and the bracket arms at the wall's ends.
    x_mid = sum(params.grip_x_range(slot)) / 2
    window = box_between(
        x_mid - GRIP_COUPON_LENGTH / 2 - 3, x_mid + GRIP_COUPON_LENGTH / 2 + 3,
        params.pocket_inner_y(slot) - 1, params.shroud_wall_outer_y + 1,
        g0 - params.pocket_rib - POCKET_COUPON_WALL, g1 + params.pocket_rib + POCKET_COUPON_WALL,
    )
    return shroud & window


FAN_MOUNT_COUPON_DEPTH = 8.0


def fan_mount_coupon(params: Params, shroud: Part) -> Part:
    """The shroud's tail end wall with a short ring of wall, plate and stub, to test the fan fit."""
    x0 = params.shroud_x_min
    window = box_between(x0 - 1, x0 + FAN_MOUNT_COUPON_DEPTH, -100, 300, -100, 300)
    return shroud & window


def coupon_parts(params: Params, parts: dict[str, Part]) -> dict[str, Part]:
    if params.mount_style == "card_clip":
        return {
            "coupon_fan_mount": fan_mount_coupon(params, parts["shroud"]),
            "coupon_grip": grip_coupon(params),
            "coupon_pocket": pocket_coupon(params, parts["shroud"]),
        }
    return {
        "coupon_fan_flange": fan_flange_coupon(params),
        "coupon_outlet_corner": outlet_corner_coupon(params, parts["duct"]),
        "coupon_pin_sizing": pin_sizing_coupon(params),
    }
