"""Assemble the parts and export STL, 3MF, STEP and PRINTING.md."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from build123d import Axis, Location, Part, Plane

from duct.coupons import coupon_parts
from duct.cover import side_cover
from duct.export import PrintPart, export_assembly, export_part
from duct.fan import fan_flange
from duct.mounts import fan_foot, foot_pin_points, pin
from duct.outlet import joint_tie_slots, outlet_frame, outlet_gasket
from duct.params import Params, load_params
from duct.plugs import blanking_plug
from duct.shroud import card_shroud, edge_grip
from duct.transition import cavity, shell, vanes
from duct.tray import floor_tray, tray_pin_points

DUCT_PRINT_ROTATION = ((Axis.Y, 90.0),)
EXAMPLE_PLUG_CHANNEL = 2


def build_duct(params: Params) -> Part:
    """Flange, lofted walls, vanes, outlet frame and the optional foot, as one solid."""
    passage = cavity(params)
    duct = fan_flange(params) + shell(params) + outlet_frame(params)
    splitters = vanes(params, passage)
    if splitters is not None:
        duct += splitters
    if params.fan_foot:
        duct += fan_foot(params)
    if params.mount_style == "card_clip":
        duct -= joint_tie_slots(params, params.outlet_x - params.gasket_lip_thickness - params.joint_tie_offset)
    return duct


def build_parts(params: Params) -> dict[str, PrintPart]:
    """Every printable part keyed by file name."""
    material = params.material
    duct = build_duct(params)
    parts = {
        "duct": PrintPart(
            "duct", duct, 1, material, "outlet face down, fan flange up", DUCT_PRINT_ROTATION,
            f"No supports; the converging walls overhang up to {params.max_half_angle():.0f} deg. Brim recommended for ABS.",
        ),
        "plug": PrintPart(
            "plug", blanking_plug(params), params.slot_positions_covered, material,
            "wedge down, plate and handle up", (), "One per empty slot channel; print only what you need.",
        ),
        "gasket": PrintPart(
            "gasket", outlet_gasket(params), 1, params.gasket_material, "flat", DUCT_PRINT_ROTATION,
            "Soft TPU between the duct's outlet frame and the shroud flange or card tails.",
        ),
    }
    if params.mount_style == "card_clip":
        parts["shroud"] = PrintPart(
            "shroud", card_shroud(params), 1, material, "side wall down, bottom plate up", ((Axis.X, -90.0),),
            "Slides over the gripped cards from the side panel; one pocket per card grip. No supports.",
        )
        for slot in range(params.slot_positions_covered):
            name = f"grip_slot{slot + 1}"
            parts[name] = PrintPart(
                name, edge_grip(params, slot), 1, params.grip_material, "back down, channel up", (),
                f"Push onto the top edge of the card in SLOT{slot + 1} ({params.card_lengths[slot]:g} mm card), "
                f"tail end {params.grip_margin:g} mm from the card tail; back {params.grip_back(slot):.1f} mm with two screw pilots. "
                f"Filament change to {params.grip_lip_material} at Z = {params.grip_lip_change_z(slot):.1f} mm.",
            )
    else:
        parts["tray"] = PrintPart(
            "tray", floor_tray(params), 1, material, "flat, upstand and rim up", (),
            "No supports. Pin holes are on the perforation grid.",
        )
        parts["pin"] = PrintPart(
            "pin", pin(params), len(tray_pin_points(params)) + len(foot_pin_points(params) if params.fan_foot else []),
            material, "head down, shaft up", (), "Print a few spares.",
        )
        if params.side_cover:
            parts["cover"] = PrintPart(
                "cover", side_cover(params), 1, material, "lid down, side wall up", ((Axis.X, 180.0),),
                "Closes the slot area above and beside the cards; butts the outlet gasket.",
            )
    if params.booster != "none":
        raise NotImplementedError(f"booster {params.booster!r} is not implemented; the plenum wall is only "
                                  f"{params.cover_lid_top_z - params.tray_top_z:.0f} mm tall")
    return parts


def assembly_instances(params: Params, parts: dict[str, PrintPart]) -> dict[str, list[Location]]:
    """Where each part sits in the duct frame: pins in their holes, one example plug in a channel."""
    instances = {name: [Location()] for name in parts}
    for slot in range(params.slot_positions_covered):
        name = f"grip_slot{slot + 1}"
        if name not in parts:
            continue
        x0, x1 = params.grip_x_range(slot)
        # Local Z (height, back at 0) maps to duct -Y: the back faces the wall, the channel faces the motherboard.
        plane = Plane(origin=((x0 + x1) / 2, params.grip_back_y(slot), params.pcb_z(slot)), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
        instances[name] = [plane.location]
    if "pin" in parts:
        head = params.pin_head_thickness
        flipped = (180.0, 0.0, 0.0)
        pins = [Location((x, y, params.tray_top_z + head), flipped) for x, y in tray_pin_points(params)]
        if params.fan_foot:
            seat = params.foot_top_z - (params.foot_height - params.tray_thickness)
            pins += [Location((x, y, seat + head), flipped) for x, y in foot_pin_points(params)]
        instances["pin"] = pins
    channel = min(EXAMPLE_PLUG_CHANNEL, params.slot_positions_covered - 1)
    y_c = (params.outlet_y_min + params.outlet_y_max) / 2
    z_c = params.outlet_z_min + (channel + 0.5) * params.slot_pitch
    plug_plane = Plane(origin=(params.outlet_x - params.plug_depth, y_c, z_c), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    instances["plug"] = [plug_plane.location] if params.place_example_plug else []
    return instances


def write_printing_md(params: Params, parts: dict[str, PrintPart], out_dir: Path, coupons: dict[str, Part]) -> Path:
    lines = [
        "# Printing",
        "",
        f"Printer: {params.printer_model} ({params.bed_x:g} x {params.bed_y:g} x {params.bed_z:g} mm, "
        f"{params.nozzle_diameter:g} mm nozzle).",
        "",
        "Each `.3mf` is already rotated into its print orientation and centred on the bed.",
        "The `.stl` files are in the duct frame for CAD use; `assembly.step` holds every part in place.",
        "",
        "## Parts",
        "",
        "| Part | Qty | Material | Orientation | Notes |",
        "|---|---|---|---|---|",
    ]
    for item in parts.values():
        bb = item.oriented(params).bounding_box()
        size = f"{bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm"
        lines.append(f"| `{item.name}.3mf` ({size}) | {item.quantity} | {item.material} | {item.orientation} | {item.notes} |")
    if coupons:
        lines += ["", "## Fit coupons", "", "| Coupon | Purpose |", "|---|---|"]
        lines.append("| `coupon_fan_flange.3mf` | Check the fan screws and the 80 mm frame seat. |")
        lines.append("| `coupon_outlet_corner.3mf` | Check the gasket lip and wall thickness. |")
        if "coupon_grip" in coupons:
            top = params.slot_positions_covered - 1
            lines.append(
                f"| `coupon_grip.3mf` | 30 mm grip, {params.grip_material} back with a filament change to "
                f"{params.grip_lip_material} at Z = {params.grip_lip_change_z(top):.1f} mm: push it onto any spare 1.57 mm PCB "
                "edge, then pull on the lips to check the two TPUs bonded. Adjust `grip_interference` if the fit is off. |"
            )
            lines.append(
                "| `coupon_pocket.3mf` | Wall slice with one pocket: the grip coupon should slide in with light "
                "friction and its back touch the pad. Adjust `pocket_clearance` if not. |"
            )
        else:
            lines.append(
                "| `coupon_pin_sizing.3mf` | Five pins, each 0.1 mm thinner than the last (notches count the steps). "
                "Set `peg_clearance` to the smallest step that presses into a midplate hole by hand. |"
            )
    lines += [
        "",
        "## Slicer settings (ElegooSlicer)",
        "",
        "- Printer profile: `Elegoo Centauri Carbon 2 0.4 nozzle`.",
        f"- Filament: `Elegoo {params.material} @ECC2` for the rigid parts. For the {params.gasket_material} gasket "
        "start from `Elegoo TPU 95A @ECC2` (no softer profile ships) and drop every speed to 20 mm/s.",
        "- Process: `0.20mm Standard @Elegoo CC2 0.4 nozzle`, then set wall loops to 4 "
        f"({4 * params.nozzle_diameter:g} mm, the configured minimum wall is {params.min_wall_thickness:g} mm).",
        "- Infill 20 % gyroid, 4 top and bottom layers.",
        "- Supports off for every part.",
        "- ABS: close the door, bed 100 C, brim 5 mm on the duct and tray, let the chamber warm for 10 minutes first.",
        "- TPU: CANVAS cannot feed it. Fit Elegoo's flexible filament adapter, disconnect the CANVAS cable, "
        "retraction off, 20 mm/s, 100 % infill, no brim.",
        f"- Grips: start in {params.grip_material}; add a filament change in ElegooSlicer at the Z given per grip "
        f"(right-click the layer slider), swap to {params.grip_lip_material} when the printer pauses. "
        "Both are TPU, so the lips bond to the back like any other layer.",
        "",
        "## Gaskets",
        "",
        f"- Outlet lip: `gasket.3mf`, {params.outlet_gasket_thickness:g} mm {params.gasket_material}, "
        "glued to the lip with a thin bead of CA. 3 mm foam tape is the fallback.",
        f"- Mount groove: {params.joint_gasket_thickness:g} mm foam tape in the tray groove under the duct's mount bar.",
        "",
    ]
    path = out_dir / "PRINTING.md"
    path.write_text("\n".join(lines))
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the PCIe card fan duct.")
    parser.add_argument("--config", default="configs/default.toml", help="TOML config path")
    parser.add_argument("--out", default="out", help="output directory")
    parser.add_argument("--coupons", action="store_true", help="also export fit coupons")
    args = parser.parse_args(argv)

    params = load_params(args.config)
    if params.unmeasured:
        print("WARNING: placeholder values still in use for: " + ", ".join(params.unmeasured), file=sys.stderr)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    parts = build_parts(params)
    for item in parts.values():
        written = export_part(item, params, out_dir)
        print(f"{item.name}: {written['stl'].name}, {written['3mf'].name} (x{item.quantity})")

    coupons: dict[str, Part] = {}
    if args.coupons:
        coupons = coupon_parts(params, {name: item.part for name, item in parts.items()})
        for name, part in coupons.items():
            rotations = DUCT_PRINT_ROTATION if name == "coupon_outlet_corner" else ()
            if name == "coupon_pocket":
                rotations = ((Axis.X, -90.0),)
            material = params.grip_material if name == "coupon_grip" else params.material
            export_part(PrintPart(name, part, 1, material, "", rotations), params, out_dir)
            print(f"{name}: exported")

    assembly = export_assembly(
        {name: item.part for name, item in parts.items()}, assembly_instances(params, parts), out_dir
    )
    print(f"assembly: {assembly.name}")
    print(f"printing notes: {write_printing_md(params, parts, out_dir, coupons).name}")
    print(
        f"transition {params.transition_length_eff:g} mm, max half-angle {params.max_half_angle():.1f} deg, "
        f"fan intake {-params.fan_intake_x:g} mm from the bracket plane "
        f"({-params.fan_intake_x - params.longest_card_length:.0f} mm past the longest card), "
        f"{params.slot_positions_covered} channels, top channel trimmed {params.top_channel_trim:.1f} mm for the GPU"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
