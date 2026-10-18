"""Assemble the parts and export STL, 3MF, STEP and PRINTING.md."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from build123d import Axis, Location, Part, Plane

from duct.coupons import GRIP_COUPON_LENGTH, coupon_parts
from duct.cover import side_cover
from duct.export import PrintPart, export_assembly, export_part
from duct.fan import fan_flange, fan_gussets, fan_screw_bores, fan_screw_tubes
from duct.mounts import fan_foot, foot_pin_points, pin
from duct.outlet import outlet_frame, outlet_gasket
from duct.params import Params, load_params
from duct.plugs import blanking_plug
from duct.shroud import card_shroud, edge_grip, edge_grip_bodies
from duct.slice import Profiles, SlicerError, export_project, slicer_available
from duct.transition import cavity, outer_body, shell, vanes
from duct.tray import floor_tray, tray_pin_points

DUCT_PRINT_ROTATION = ((Axis.Y, 90.0),)
EXAMPLE_PLUG_CHANNEL = 2


def build_duct(params: Params) -> Part:
    """Flange, lofted walls, vanes, outlet frame and the optional foot, as one solid."""
    passage = cavity(params)
    duct = fan_flange(params) + shell(params) + outlet_frame(params)
    # Gussets behind the flange's corner pads, kept inside the duct's envelope so nothing pokes out
    # below the converging walls.
    duct += fan_gussets(params) & outer_body(params)
    # Sealed tubes around the fan screw axes, then the head bores through to the outlet face.
    duct += fan_screw_tubes(params)
    splitters = vanes(params, passage)
    if splitters is not None:
        duct += splitters
    if params.fan_foot:
        duct += fan_foot(params)
    return duct - fan_screw_bores(params)


def card_clip_parts(params: Params) -> dict[str, PrintPart]:
    """Card-clip build: one shroud with the tail fan wall and bracket tab, plus a TPU grip per card."""
    parts = {
        "shroud": PrintPart(
            "shroud", card_shroud(params), 1, params.material, "standing on its tail end wall, bracket end up",
            ((Axis.Y, -90.0),),
            f"Slides over the gripped cards from the side panel; one pocket per card grip. The {params.tail_fan_size:g} mm "
            "fan bolts onto the tail end wall; each rib's ear goes under its card's PCI bracket screw. No supports; use a brim.",
        ),
    }
    for slot in range(params.slot_positions_covered):
        name = f"grip_slot{slot + 1}"
        parts[name] = PrintPart(
            name, edge_grip(params, slot), 1, f"{params.grip_material} back, {params.grip_lip_material} lips",
            "back down, channel up", (),
            f"Push onto the top edge of the card in SLOT{slot + 1} ({params.card_lengths[slot]:g} mm card), "
            f"tail end {params.grip_margin:g} mm from the card tail; back {params.grip_back(slot):.1f} mm with "
            f"{len(params.grip_screw_positions(slot))} screw pilots. One object, two parts: `{name}_back` on "
            f"filament 1 ({params.grip_material}), `{name}_lips` on filament 2 ({params.grip_lip_material}).",
            bodies=edge_grip_bodies(params, slot),
            body_materials={"back": params.grip_material, "lips": params.grip_lip_material},
        )
    return parts


def build_parts(params: Params) -> dict[str, PrintPart]:
    """Every printable part keyed by file name."""
    material = params.material
    if params.mount_style == "card_clip":
        return card_clip_parts(params)
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
    if "plug" not in parts:
        return instances
    channel = min(EXAMPLE_PLUG_CHANNEL, params.slot_positions_covered - 1)
    y_c = (params.outlet_y_min + params.outlet_y_max) / 2
    z_c = params.outlet_z_min + (channel + 0.5) * params.slot_pitch
    plug_plane = Plane(origin=(params.outlet_x - params.plug_depth, y_c, z_c), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    instances["plug"] = [plug_plane.location] if params.place_example_plug else []
    return instances


def write_printing_md(params: Params, parts: dict[str, PrintPart], out_dir: Path, coupons: dict[str, Part]) -> Path:
    card_clip = params.mount_style == "card_clip"
    lines = [
        "# Printing",
        "",
        f"Printer: {params.printer_model} ({params.bed_x:g} x {params.bed_y:g} x {params.bed_z:g} mm, "
        f"{params.nozzle_diameter:g} mm nozzle).",
        "",
        "Each `.3mf` is a project file written by ElegooSlicer itself: printer, process and filament presets are",
        "embedded and the part is already rotated into its print orientation and centred on the bed. Open it,",
        "check the filament mapping, slice. The `.stl` files in `out/` are in the duct frame for CAD use,",
        "`out/oriented/` holds the print-oriented meshes and `out/assembly.step` every part in place.",
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
        if "coupon_fan_mount" in coupons:
            lines.append(
                f"| `coupon_fan_mount.3mf` | The tail end wall: screw the {params.tail_fan_size:g} mm fan on with its own fan "
                "screws from the inside; the frame must sit square and the screws bite. |"
            )
        else:
            lines.append("| `coupon_fan_flange.3mf` | Screw the fan on from the back with its own fan screws: the heads must drop "
                         f"into the {params.fan_screw_head_clearance:g} mm bores and seat flat. |")
            lines.append("| `coupon_outlet_corner.3mf` | Check the gasket lip and wall thickness. |")
        if "coupon_grip" in coupons:
            top = params.slot_positions_covered - 1
            lines.append(
                f"| `coupon_grip.3mf` | 30 mm grip built like the real ones: {params.grip_material} back on filament 1, "
                f"{params.grip_lip_material} lips on filament 2 from Z = {params.grip_lip_change_z(top):.1f} mm. Push it onto "
                "any spare 1.57 mm PCB edge, then pull on the lips to check the two TPUs bonded. "
                "Adjust `grip_interference` if the fit is off. |"
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
        "Every project already carries these, so there is nothing to set by hand:",
        "",
        "- Printer: `Elegoo Centauri Carbon 2 0.4 nozzle`.",
        f"- Filaments: `Elegoo {params.material} @ECC2` for the rigid parts, `Elegoo TPU 95A @ECC2` for TPU 95A and "
        "`Elegoo TPU 72D @ECC2` for TPU 72D. ElegooSlicer ships no 72D preset, so that one is derived from the 95A preset "
        "with Elegoo's 72D temperatures (230 C nozzle, 40 C bed, `configs/filament_tpu72d.json`) and travels inside "
        "the project.",
        f"- Process: `0.20mm Standard @Elegoo CC2 0.4 nozzle` with 4 wall loops ({4 * params.nozzle_diameter:g} mm, the "
        f"configured minimum wall is {params.min_wall_thickness:g} mm), 20 % gyroid infill, 4 top and bottom layers, "
        "5 mm outer brim and no supports (`configs/slicer_overrides.json`); TPU parts get 100 % infill and no brim "
        "(`configs/slicer_overrides_tpu.json`).",
        "",
        "At the printer:",
        "",
        "- ABS: the preset sets 270 C nozzle, 90 C bed on the textured PEI plate and a 5 mm brim on "
        f"{'the shroud' if card_clip else 'the duct and tray'}. The chamber has no heater: close the door and louvres, start the bed and "
        "let it warm the chamber for 10 minutes before the print begins, watching the printer's chamber readout.",
    ]
    if card_clip:
        lines += [
            f"- Fan: a {params.tail_fan_size:g} mm fan ({params.tail_fan_hole_spacing:g} mm hole spacing), airflow arrow "
            "pointing into the shroud. Before the shroud goes on, hold the fan against the tail end wall's outer face and "
            f"drive its four standard {params.fan_screw_length:g} mm fan screws from inside the shroud, through the wall into "
            "the fan frame's own holes; reach them from the shroud's open motherboard side.",
            "- Bracket tab: loosen the screws of the covered cards' brackets, slide the tab under their heads, retighten. "
            f"The tab adds {params.bracket_tab_thickness:g} mm under each head, so the screws may need to be that much longer.",
        ]
    else:
        lines.append(
            f"- Fan: before the shroud goes on, hold the fan on the flange and drive four standard {params.fan_screw_length:g} mm "
            "fan screws from the outlet side down the bores in the duct's corners, through the flange into the fan frame's "
            f"own holes. Use a driver with a shaft under {params.fan_screw_head_clearance:g} mm."
        )
    lines += [
        "- TPU: feed it through CANVAS like any other spool; dry the 72D first (70 C, 8 h) if the spool has been open.",
    ]
    if card_clip:
        lines.append(
            f"- Grips: one object with two parts, the back on filament 1 ({params.grip_material}) and the lips on "
            f"filament 2 ({params.grip_lip_material}). Map the two filaments to the CANVAS slots holding those spools and "
            "the printer swaps by itself; with one spool, point both filaments at it and add a filament change at "
            f"Z = {params.grip_back(0):.1f} mm. Both are TPU, so the lips bond to the back like any other layer."
        )
    if not card_clip:
        lines += ["", "## Gaskets", ""]
        lines += [
            f"- Outlet lip: `gasket.3mf`, {params.outlet_gasket_thickness:g} mm {params.gasket_material}, "
            "glued to the lip with a thin bead of CA. 3 mm foam tape is the fallback.",
            f"- Mount groove: {params.joint_gasket_thickness:g} mm foam tape in the tray groove under the duct's mount bar.",
        ]
    lines.append("")
    path = out_dir / "PRINTING.md"
    path.write_text("\n".join(lines))
    return path


def write_project(item: PrintPart, oriented: list[Path], out_dir: Path, profiles: Profiles) -> Path:
    """Have ElegooSlicer write out/<name>.3mf: every body on its own filament, merged into one object."""
    materials = [material for _, _, material in item.filament_bodies()]
    kind = "tpu" if all(material.startswith("TPU") for material in materials) else "rigid"
    filaments = [profiles.filament(material) for material in materials]
    return export_project(oriented, filaments, profiles.machine(), profiles.process(kind), out_dir / f"{item.name}.3mf", item.name)


def coupon_print_parts(params: Params, coupons: dict[str, Part]) -> dict[str, PrintPart]:
    """Coupons as print parts: orientation per coupon, the grip coupon two-material like the real grips."""
    items = {}
    for name, part in coupons.items():
        rotations: tuple = DUCT_PRINT_ROTATION if name == "coupon_outlet_corner" else ()
        if name == "coupon_pocket":
            rotations = ((Axis.X, -90.0),)
        if name == "coupon_fan_mount":
            rotations = ((Axis.Y, -90.0),)
        item = PrintPart(name, part, 1, params.material, "", rotations)
        if name == "coupon_grip":
            slot = params.slot_positions_covered - 1
            item.material = f"{params.grip_material} back, {params.grip_lip_material} lips"
            item.bodies = edge_grip_bodies(params, slot, length=GRIP_COUPON_LENGTH)
            item.body_materials = {"back": params.grip_material, "lips": params.grip_lip_material}
        items[name] = item
    return items


def fill_print_dir(print_dir: Path, out_dir: Path, parts: dict[str, PrintPart], coupons: dict[str, Part], notes: Path) -> int:
    """Replace print_dir with the project 3MF of every part in this build, the printing notes, and any coupons."""
    if print_dir.exists():
        shutil.rmtree(print_dir)
    print_dir.mkdir(parents=True)
    count = 0
    for name in parts:
        shutil.copy2(out_dir / f"{name}.3mf", print_dir / f"{name}.3mf")
        count += 1
    shutil.copy2(notes, print_dir / notes.name)
    count += 1
    if coupons:
        coupon_dir = print_dir / "coupons"
        coupon_dir.mkdir()
        for name in coupons:
            shutil.copy2(out_dir / f"{name}.3mf", coupon_dir / f"{name}.3mf")
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the PCIe card fan duct.")
    parser.add_argument("--config", default="configs/default.toml", help="TOML config path")
    parser.add_argument("--out", default="out", help="output directory")
    parser.add_argument("--coupons", action="store_true", help="also export fit coupons")
    parser.add_argument("--print-dir", default=None, help="directory to fill with just the print-ready 3MF files")
    args = parser.parse_args(argv)

    params = load_params(args.config)
    if params.unmeasured:
        print("WARNING: placeholder values still in use for: " + ", ".join(params.unmeasured), file=sys.stderr)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if slicer_available():
        work = tempfile.TemporaryDirectory()
        profiles: Profiles | None = Profiles(Path(work.name))
    else:
        profiles = None
        message = "elegooslicer not found: no project 3MF files written"
        if args.print_dir:
            print(f"ERROR: {message}; the print set needs them", file=sys.stderr)
            return 1
        print(f"WARNING: {message}", file=sys.stderr)

    def export(item: PrintPart) -> str:
        written = export_part(item, params, out_dir)
        names = [written["stl"].name]
        if profiles is not None:
            try:
                names.append(write_project(item, written["oriented"], out_dir, profiles).name)
            except SlicerError as error:
                print(f"ERROR: {error}", file=sys.stderr)
                raise SystemExit(1) from error
        return ", ".join(names)

    parts = build_parts(params)
    for item in parts.values():
        print(f"{item.name}: {export(item)} (x{item.quantity})")

    coupons: dict[str, Part] = {}
    if args.coupons:
        coupons = coupon_parts(params, {name: item.part for name, item in parts.items()})
        for item in coupon_print_parts(params, coupons).values():
            print(f"{item.name}: {export(item)}")

    assembly = export_assembly(
        {name: item.part for name, item in parts.items()}, assembly_instances(params, parts), out_dir
    )
    print(f"assembly: {assembly.name}")
    notes = write_printing_md(params, parts, out_dir, coupons)
    print(f"printing notes: {notes.name}")
    if args.print_dir:
        copied = fill_print_dir(Path(args.print_dir), out_dir, parts, coupons, notes)
        print(f"print set: {copied} files in {args.print_dir}/")
    if params.mount_style == "card_clip":
        print(
            f"shroud {-params.shroud_x_min:g} mm from the bracket plane, {params.tail_fan_size:g} mm fan intake "
            f"{-params.tail_fan_intake_x:g} mm ({-params.tail_fan_intake_x - params.longest_card_length:.0f} mm past the "
            f"longest card), fan {params.tail_fan_center_z_eff - params.tail_fan_size / 2 - params.midplate_z:.1f} mm "
            f"above the midplate and {params.gpu_plane_z - params.tail_fan_center_z_eff - params.tail_fan_size / 2:.1f} mm "
            "under the GPU"
        )
    else:
        print(
            f"transition {params.transition_length_eff:g} mm, max half-angle {params.max_half_angle():.1f} deg, "
            f"fan intake {-params.fan_intake_x:g} mm from the bracket plane "
            f"({-params.fan_intake_x - params.longest_card_length:.0f} mm past the longest card), "
            f"{params.slot_positions_covered} channels, top channel trimmed {params.top_channel_trim:.1f} mm for the GPU"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
