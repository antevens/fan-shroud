"""Draw the duct in its case context: side section, outlet-face view and a 3D render.

Context geometry (cards, GPU, PSU) is illustrative; the duct, tray, pins, plug and gasket come from the build.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

if "DISPLAY" not in os.environ and shutil.which("xvfb-run"):
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    os.execvp("xvfb-run", ["xvfb-run", "-a", "-s", "-screen 0 1280x1024x24", sys.executable, __file__, *sys.argv[1:]])

import matplotlib
import numpy as np
import pyrender
import trimesh
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.font_manager  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from duct.build import EXAMPLE_PLUG_CHANNEL, assembly_instances, build_parts  # noqa: E402
from duct.mounts import foot_pin_points  # noqa: E402
from duct.params import load_params  # noqa: E402
from duct.transition import vane_planes  # noqa: E402
from duct.tray import tray_pin_points  # noqa: E402

OUT = Path(__file__).resolve().parent
SUFFIX = ""
# slot index (0 = bottom = SLOT1) -> (card, length). SLOT1 X540-T2, SLOT2 ConnectX-5 Ex, SLOT3 Broadcom P210P.
CARD_LENGTHS = {0: ("XZSNET X540", 152.0), 1: ("MCX556N", 142.24), 2: ("Dell 57412", 167.64)}
GPU_BACKPLATE = 3.0
PSU_DEPTH = 8.0
HEATSINK_DEPTH = 14.5
PCB_THICKNESS = 1.6

C_DUCT = "#2b6cb0"
C_TRAY = "#2f855a"
C_PIN = "#805ad5"
C_PLUG = "#dd6b20"
C_GASKET = "#d53f8c"
C_COVER = "#b7791f"
C_SHROUD = "#b7791f"
C_GRIP = "#9f7aea"
C_CASE = "#4a5568"
C_CARD = "#718096"
C_GPU = "#a0aec0"
C_AIR = "#0987a0"


def rect(ax, x0, x1, z0, z1, **kw):
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, **kw))


def side_section(p) -> Path:
    fig, ax = plt.subplots(figsize=(16, 9), dpi=110)
    z_pcb = [k * p.slot_pitch + p.channel_floor_below_pcb for k in range(p.slot_positions_covered)]
    gpu_z0 = p.gpu_plane_z
    gpu_z1 = p.gpu_pcb_z + GPU_BACKPLATE
    plugged = min(EXAMPLE_PLUG_CHANNEL, p.slot_positions_covered - 1)
    plugged = plugged if plugged not in CARD_LENGTHS else None

    # Case context
    rect(ax, -310, 5, p.midplate_z - 0.8, p.midplate_z, color=C_CASE)
    rect(ax, -310, 5, p.midplate_z - p.under_midplate_gap - PSU_DEPTH, p.midplate_z - p.under_midplate_gap, color="#cbd5e0")
    ax.text(-300, p.midplate_z - p.under_midplate_gap - PSU_DEPTH / 2, "PSU", va="center", fontsize=9)
    ax.annotate("", xy=(-140, p.midplate_z), xytext=(-140, p.midplate_z - p.under_midplate_gap),
                arrowprops=dict(arrowstyle="<->", color=C_CASE))
    ax.text(-138, p.midplate_z - p.under_midplate_gap / 2, f"under-midplate gap {p.under_midplate_gap:g} (bypass)", va="center", fontsize=8)
    for x in np.arange(-308, 2, 4):
        covered = p.tray_x_min <= x <= p.tray_x_max
        ax.plot([x], [p.midplate_z - 0.4], "o", ms=2, color="white" if not covered else C_CASE, zorder=3)
    rect(ax, 0, 4, p.midplate_z, gpu_z1 + 10, color=C_CASE)
    ax.text(5, gpu_z1 / 2, "rear panel / brackets (x = 0)", rotation=90, va="center", fontsize=9)
    sealed = "nothing rests on it" if p.mount_style == "card_clip" else "card zone sealed by the tray"
    ax.text(-205, p.midplate_z - 6, f"midplate: {sealed}", fontsize=9, color=C_CASE)
    ax.text(-311, p.midplate_z - 6, "intake zone open", fontsize=9, color=C_CASE)
    ax.text(-19, p.midplate_z - 6, "exhaust\nzone open", fontsize=8, color=C_CASE)

    # Cards
    for k, z in enumerate(z_pcb):
        card = CARD_LENGTHS.get(k)
        if card is None:
            ax.text(-100, z - 8, f"SLOT{k + 1}: empty, channel plugged", fontsize=9, color=C_PLUG, ha="center")
            continue
        name, length = card
        rect(ax, -length, 0, z - PCB_THICKNESS, z, color=C_CARD)
        rect(ax, -length + 25, -45, z - PCB_THICKNESS - HEATSINK_DEPTH, z - PCB_THICKNESS, facecolor="none",
             edgecolor=C_CARD, hatch="|||")
        ax.text(-2, z - PCB_THICKNESS - 1.5, f"SLOT{k + 1}: {name} {length:g} mm", fontsize=8, ha="right", va="top")
    rect(ax, -p.gpu_length, 0, gpu_z0, gpu_z1, color=C_GPU)
    ax.text(-130, gpu_z0 + (gpu_z1 - gpu_z0) / 2,
            f"GPU in SLOT6 (344 x 128 x 55 mm, blocks SLOT5 and SLOT4): fans on its underside draw air UP,\n"
            "exhaust leaves through the card's edges and its vented tail",
            ha="center", va="center", fontsize=10)
    for x in (-180, -100):
        ax.annotate("", xy=(x, gpu_z0 + 1), xytext=(x, gpu_z0 - 9), arrowprops=dict(arrowstyle="->", color="#c53030", lw=1.5))
    ax.text(-268, gpu_z1 + 4, f"GPU underside {p.gpu_clearance:.1f} mm above the SLOT3 channel grid line;\n"
            f"{'stub' if p.mount_style == 'card_clip' else 'lid'} top {gpu_z0 - (p.outlet_z_max + p.wall_thickness):.1f} mm under it", fontsize=7, color="#c53030", va="bottom", ha="left")

    # Fan
    fan_z0 = p.fan_center_z_eff - p.fan_size / 2
    rect(ax, p.fan_intake_x, p.fan_face_x, fan_z0, fan_z0 + p.fan_size, facecolor="#edf2f7", edgecolor="black")
    ax.text((p.fan_intake_x + p.fan_face_x) / 2, p.fan_center_z_eff, "80 mm\nfan", ha="center", va="center", fontsize=10)
    for z in (p.fan_center_z_eff - 25, p.fan_center_z_eff, p.fan_center_z_eff + 25):
        ax.annotate("", xy=(p.fan_intake_x - 1, z), xytext=(p.fan_intake_x - 16, z), arrowprops=dict(arrowstyle="->", color=C_AIR, lw=2))
    ax.annotate("", xy=(p.fan_intake_x - 6, fan_z0 + 2), xytext=(p.fan_intake_x - 6, p.midplate_z + 1), arrowprops=dict(arrowstyle="->", color=C_AIR, lw=2))
    ax.text(p.fan_intake_x - 18, p.midplate_z + 2, "fresh air from\nthe case front", fontsize=8, ha="right", va="bottom", color=C_AIR)

    # Duct outline
    oz0, oz1 = p.wall_normal_offset("z_min"), p.wall_normal_offset("z_max")
    body = [
        (p.fan_inner_x, p.fan_inner_z_min - oz0), (p.outlet_x, p.outlet_z_min - oz0),
        (p.outlet_x, p.outlet_z_max + oz1), (p.fan_inner_x, p.fan_inner_z_max + oz1),
    ]
    ax.add_patch(Polygon(body, closed=True, facecolor="#bee3f8", edgecolor=C_DUCT, lw=1.5))
    inner = [
        (p.fan_inner_x, p.fan_inner_z_min), (p.outlet_x, p.outlet_z_min),
        (p.outlet_x, p.outlet_z_max), (p.fan_inner_x, p.fan_inner_z_max),
    ]
    ax.add_patch(Polygon(inner, closed=True, facecolor="white", edgecolor=C_DUCT, lw=1))
    for z_fan, z_out in vane_planes(p):
        ax.plot([p.fan_inner_x, p.outlet_x], [z_fan, z_out], color=C_DUCT, lw=1.6)
    rect(ax, p.fan_face_x, p.fan_inner_x, p.flange_bottom_z, p.flange_bottom_z + p.fan_flange_size, color=C_DUCT)
    ax.text(-268, p.fan_end_top_z + 2, f"fan intake {-p.fan_intake_x:.0f} mm from the brackets,\n"
            f"{-p.fan_intake_x - p.longest_card_length:.0f} mm past the longest card", fontsize=8, color=C_DUCT, ha="left", va="top")
    y0, y1, fz0, fz1 = p.frame_bounds()
    rect(ax, p.outlet_x - p.gasket_lip_thickness, p.outlet_x, fz0, fz1, color=C_DUCT)
    rect(ax, p.outlet_x - p.gasket_lip_thickness, p.outlet_x, p.mount_bar_bottom_z, fz0, color=C_DUCT)
    foot = [
        (p.foot_x_min, p.midplate_z), (p.foot_flat_x_max, p.midplate_z), (p.foot_x_max, p.foot_rim_top_z),
        (p.fan_face_x, p.foot_rim_top_z), (p.fan_face_x, p.foot_top_z), (p.foot_x_min, p.foot_top_z),
    ]
    ax.add_patch(Polygon(foot, closed=True, facecolor=C_DUCT, edgecolor=C_DUCT))
    rect(ax, p.outlet_x, p.outlet_x + p.outlet_gasket_thickness, fz0, p.outlet_z_min, color=C_GASKET)
    rect(ax, p.outlet_x, p.outlet_x + p.outlet_gasket_thickness, p.outlet_z_max, fz1, color=C_GASKET)
    ax.text(p.fan_face_x - 4, p.fan_center_z_eff + 10, f"duct: {p.slot_positions_covered} channels,\nconverging from\nthe 80 mm fan",
            ha="right", fontsize=9, color=C_DUCT, va="center")
    if p.fan_foot:
        ax.text(p.foot_x_max + 2, p.midplate_z - 6, "foot, pinned into\nintake perforations", fontsize=8, color=C_DUCT, va="top")
    if p.side_cover and p.mount_style == "case":
        rect(ax, p.cover_x_min, p.cover_x_max, p.cover_lid_bottom_z, p.cover_lid_top_z, color=C_COVER)
        ax.annotate("cover lid; its side wall stands between the cards and the viewer", xy=(-60, p.cover_lid_top_z),
                    xytext=(-60, gpu_z1 + 4), fontsize=8, color=C_COVER, ha="center", va="bottom",
                    arrowprops=dict(arrowstyle="->", color=C_COVER))

    if p.mount_style == "card_clip":
        rect(ax, p.shroud_x_min, p.stub_x_max, p.outlet_z_max, p.outlet_z_max + p.wall_thickness, color=C_SHROUD)
        rect(ax, p.shroud_x_min, p.shroud_x_max, p.shroud_bottom_z, p.outlet_z_min, color=C_SHROUD)
        ax.plot([p.shroud_x_min, p.shroud_x_max], [p.shroud_top_z, p.shroud_top_z], color=C_SHROUD, ls=":", lw=1.5)
        fy0, fy1, fz0, fz1 = p.frame_bounds()
        rect(ax, p.shroud_x_min, p.shroud_x_min + p.gasket_lip_thickness, fz0, fz1, color=C_SHROUD)
        for slot in range(p.slot_positions_covered):
            gx0, gx1 = p.grip_x_range(slot)
            gz = p.grip_outer_width / 2
            rect(ax, gx0, gx1, p.pcb_z(slot) - gz, p.pcb_z(slot) + gz, facecolor="none", edgecolor=C_GRIP, ls="--", lw=1.2)
        ax.text(-2, gpu_z1 + 4, "shroud (ochre): bottom plate, stub over the top card's tail, side wall toward the viewer (dotted: its top edge);\n"
                "no lid, the top card's PCB is the roof. Dashed purple: TPU grips on the card edges",
                fontsize=8, color=C_SHROUD, ha="right", va="bottom")
        ax.text(p.shroud_x_min + 3, p.shroud_bottom_z - 3, "gasket (pink) + flange + zip ties join duct and shroud", fontsize=8,
                color=C_GASKET, ha="left", va="top")
        return finish_side(fig, ax, p, gpu_z1)
    # Tray
    rect(ax, p.tray_x_min, p.tray_x_max, p.midplate_z, p.tray_top_z, color=C_TRAY)
    rect(ax, p.upstand_x_min, p.upstand_x_max, p.tray_top_z, p.groove_floor_z, color=C_TRAY)
    rect(ax, p.upstand_x_min, p.groove_x_min, p.groove_floor_z, p.fence_top_z, color=C_TRAY)
    rect(ax, p.groove_x_max, p.upstand_x_max, p.groove_floor_z, p.fence_top_z, color=C_TRAY)
    rect(ax, p.tray_x_max - p.tray_lip_width, p.tray_x_max, p.tray_top_z, p.tray_top_z + p.tray_lip_height, color=C_TRAY)
    ax.text(-100, p.tray_top_z + 3, f"floor tray {p.tray_thickness:g} mm, slot pegs, seals card-zone perforations", fontsize=9, color=C_TRAY, ha="center")
    ax.annotate("mount bar drops into\ngasketed tray groove", xy=(p.outlet_x - 1, p.mount_bar_bottom_z + 2), xytext=(-165, -11),
                fontsize=8, va="center", arrowprops=dict(arrowstyle="->", color="black"))
    pins = [(x, p.tray_top_z) for x, _ in tray_pin_points(p)]
    if p.fan_foot:
        seat = p.foot_top_z - (p.foot_height - p.tray_thickness)
        pins += [(x, seat) for x, _ in foot_pin_points(p)]
    for x, z_seat in dict.fromkeys(pins):
        rect(ax, x - p.pin_head_diameter / 2, x + p.pin_head_diameter / 2, z_seat, z_seat + p.pin_head_thickness, color=C_PIN)
        rect(ax, x - p.pin_diameter / 2, x + p.pin_diameter / 2, z_seat - p.pin_shaft_length, z_seat, color=C_PIN)
    ax.text(-95, p.midplate_z - 7, "press-in slot pegs", fontsize=8, color=C_PIN, ha="center", va="top")

    # Plug, only when the example channel's slot is empty
    if plugged is not None:
        z_c = (plugged + 0.5) * p.slot_pitch
        half_wide = (p.slot_pitch - p.vane_thickness - 2 * p.plug_clearance) / 2
        wedge = [(p.outlet_x - p.plug_depth, z_c - half_wide), (p.outlet_x, z_c - half_wide),
                 (p.outlet_x, z_c + half_wide), (p.outlet_x - p.plug_depth, z_c + half_wide)]
        ax.add_patch(Polygon(wedge, closed=True, color=C_PLUG))
        rect(ax, p.outlet_x, p.outlet_x + p.plug_plate_thickness, z_c - p.slot_pitch / 2 + 0.1, z_c + p.slot_pitch / 2 - 0.1, color=C_PLUG)
        rect(ax, p.outlet_x + p.plug_plate_thickness, p.outlet_x + p.plug_plate_thickness + p.plug_handle_height,
             z_c - p.plug_handle_thickness / 2, z_c + p.plug_handle_thickness / 2, color=C_PLUG)
        ax.text(p.outlet_x + 12, z_c, "blanking plug", fontsize=8, color=C_PLUG, va="center")

    # Airflow
    for kk in range(p.slot_positions_covered):
        z_mid = (kk + 0.5) * p.slot_pitch
        if kk == plugged:
            continue
        ax.annotate("", xy=(p.outlet_x - 2, z_mid), xytext=(p.outlet_x - 16, z_mid), arrowprops=dict(arrowstyle="->", color=C_AIR, lw=2))
        for x in (-150, -105, -60):
            ax.annotate("", xy=(x + 22, z_mid - 4), xytext=(x, z_mid - 4), arrowprops=dict(arrowstyle="->", color=C_AIR, lw=2))
    ax.annotate("", xy=(-10, gpu_z0 - 4), xytext=(-10, 10), arrowprops=dict(arrowstyle="->", color=C_AIR, lw=2))
    ax.text(-4, gpu_z1 + 12, "exhaust gap: air turns up to the top/rear fans\nand out toward the side panel", fontsize=8, color=C_AIR, ha="right", va="bottom")

    return finish_side(fig, ax, p, gpu_z1)


def finish_side(fig, ax, p, gpu_z1) -> Path:
    ax.set_xlim(p.fan_intake_x - 60, 22)
    ax.set_ylim(p.midplate_z - p.under_midplate_gap - PSU_DEPTH - 4, gpu_z1 + 24)
    ax.set_aspect("equal")
    ax.set_xlabel("X: along the cards, mm (0 = bracket plane, case front to the left)")
    ax.set_ylabel("Z: vertical, mm (0 = floor of bottom channel)")
    mount = "shroud riding on the cards" if p.mount_style == "card_clip" else "lid, side wall and tray"
    ax.set_title(f"Side section from the side panel: slim 80 mm fan converging into 3 channels under the GPU; {mount} close the plenum")
    ax.grid(alpha=0.2)
    path = OUT / f"side_section{SUFFIX}.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def outlet_view(p) -> Path:
    fig, ax = plt.subplots(figsize=(11, 10), dpi=110)
    z_pcb = [k * p.slot_pitch + p.channel_floor_below_pcb for k in range(p.slot_positions_covered)]
    gpu_z0 = p.gpu_plane_z
    gpu_z1 = p.gpu_pcb_z + GPU_BACKPLATE
    foam_y = p.card_top_height + p.side_clearance
    plugged = min(EXAMPLE_PLUG_CHANNEL, p.slot_positions_covered - 1)
    plugged = plugged if plugged not in CARD_LENGTHS else None

    rect(ax, -4, 0, p.midplate_z - 30, gpu_z1 + 10, color=C_CASE)
    ax.text(-6, 60, "motherboard surface (y = 0)", rotation=90, va="center", ha="right", fontsize=9)
    rect(ax, 0, foam_y + 20, p.midplate_z - 0.8, p.midplate_z, color=C_CASE)
    ax.text(foam_y - 2, p.midplate_z - 5, "midplate", fontsize=9, ha="right", color=C_CASE)
    rect(ax, foam_y, foam_y + 6, p.midplate_z - 30, gpu_z1 + 10, facecolor="#e2e8f0", edgecolor=C_CASE, hatch="///")
    ax.text(foam_y + 7, 60, f"side panel foam (side_clearance {p.side_clearance:g}, TODO)", rotation=90, va="center", fontsize=9)

    for k, z in enumerate(z_pcb):
        rect(ax, 0, p.connector_height, z - 3.5, z + 3.5, color="#1a202c")
        if k == plugged:
            continue
        rect(ax, p.connector_height, p.card_top_height, z - PCB_THICKNESS, z, color=C_CARD)
        rect(ax, 20, p.card_top_height - 8, z - PCB_THICKNESS - HEATSINK_DEPTH, z - PCB_THICKNESS, facecolor="none", edgecolor=C_CARD, hatch="|||")
    rect(ax, 0, 128, gpu_z0, gpu_z1, color=C_GPU)
    ax.text(64, (gpu_z0 + gpu_z1) / 2, "GPU (128 mm tall)", ha="center", va="center", fontsize=11)

    y0, y1, fz0, fz1 = p.frame_bounds()
    rect(ax, y0, y1, fz0, fz1, color=C_DUCT)
    rect(ax, p.outlet_y_min, p.outlet_y_max, p.outlet_z_min, p.outlet_z_max, color="white")
    for z in p.channel_boundaries_z[1:-1]:
        rect(ax, p.outlet_y_min, p.outlet_y_max, z - p.vane_thickness / 2, z + p.vane_thickness / 2, color=C_DUCT)
    rect(ax, y0, y1, p.mount_bar_bottom_z, fz0, color=C_DUCT)
    for k in range(p.slot_positions_covered):
        if k == plugged:
            continue
        z_mid = (p.channel_boundaries_z[k] + p.channel_boundaries_z[k + 1]) / 2
        ax.text((p.outlet_y_min + p.outlet_y_max) / 2, z_mid, f"channel {k + 1}  ->  SLOT{k + 1}", ha="center", va="center", fontsize=9, color=C_DUCT)
    ax.text((y0 + y1) / 2, fz1 + 3, f"outlet {p.card_zone_height:.1f} x {p.outlet_z_max:.1f} mm with its gasket frame", ha="center", fontsize=9, color=C_DUCT)

    if plugged is not None:
        z_c = (plugged + 0.5) * p.slot_pitch
        rect(ax, p.outlet_y_min + p.plug_clearance, p.outlet_y_max - p.plug_clearance, z_c - p.slot_pitch / 2 + 0.1, z_c + p.slot_pitch / 2 - 0.1,
             facecolor=C_PLUG, alpha=0.85)
        yc = (p.outlet_y_min + p.outlet_y_max) / 2
        rect(ax, yc - p.plug_handle_length / 2, yc + p.plug_handle_length / 2, z_c - p.plug_handle_thickness / 2, z_c + p.plug_handle_thickness / 2, color="#7b341e")
        ax.text(p.outlet_y_max + 3, z_c, "plug (empty slot)", fontsize=8, color=C_PLUG, va="center")

    if p.mount_style == "card_clip":
        rect(ax, p.shroud_wall_inner_y, p.shroud_wall_outer_y, p.shroud_bottom_z, p.shroud_top_z, color=C_SHROUD)
        rect(ax, p.cover_y_min, p.shroud_wall_outer_y, p.shroud_bottom_z, p.outlet_z_min, color=C_SHROUD)
        for slot in range(p.slot_positions_covered):
            for rz0, rz1 in p.pocket_rib_z_ranges(slot):
                rect(ax, p.pocket_inner_y(slot), p.shroud_wall_inner_y, rz0, rz1, color=C_SHROUD)
            gz = p.grip_outer_width / 2
            top = p.card_top_edge(slot)
            rect(ax, top - p.grip_engagement, p.grip_back_y(slot), p.pcb_z(slot) - gz, p.pcb_z(slot) + gz, color=C_GRIP)
            rect(ax, top - p.grip_engagement - 0.5, top, p.pcb_z(slot) - p.pcb_thickness / 2, p.pcb_z(slot) + p.pcb_thickness / 2, color=C_CARD)
            ax.text(p.pocket_inner_y(slot) - 2, p.pcb_z(slot), f"PCB {p.card_pcb_heights[slot]:g} mm, grip back {p.grip_back(slot):.1f} mm",
                    fontsize=7, color=C_GRIP, ha="right", va="center")
        fill = ("wall fixed at the 68.9 mm reference, pockets identical; each grip's back grows to reach the wall"
                if p.grip_fill == "grip" else "a pad in the pocket fills to the wall")
        ax.text(p.shroud_wall_outer_y + 3, (p.shroud_bottom_z + p.shroud_top_z) / 2,
                f"shroud wall with a pocket per card (ribs);\nTPU grip (purple) {p.grip_engagement:g} mm down each PCB face;\n{fill};\nno lid, the top PCB is the roof",
                fontsize=8, color=C_SHROUD, va="center")
    elif p.side_cover:
        rect(ax, p.cover_y_inner, p.cover_y_outer, p.tray_top_z, p.cover_lid_top_z, color=C_COVER)
        rect(ax, p.cover_y_min, p.cover_y_outer, p.cover_lid_bottom_z, p.cover_lid_top_z, color=C_COVER)
        ax.text(p.cover_y_outer + 3, (p.tray_top_z + p.cover_lid_top_z) / 2, "cover: side wall and lid\n(section behind the outlet frame)",
                fontsize=8, color=C_COVER, va="center")

    if p.mount_style == "case":
        rect(ax, p.tray_y_min, p.tray_y_max, p.midplate_z, p.tray_top_z, color=C_TRAY)
        rect(ax, p.tray_y_min, p.tray_y_max, p.tray_top_z, p.groove_floor_z, color=C_TRAY)
        rect(ax, p.tray_y_min, p.tray_y_max, p.groove_floor_z, p.fence_top_z, facecolor=C_TRAY, alpha=0.35)
        rect(ax, p.tray_y_min, y0 - p.mount_groove_clearance, p.groove_floor_z, p.fence_top_z, color=C_TRAY)
        rect(ax, y1 + p.mount_groove_clearance, p.tray_y_max, p.groove_floor_z, p.fence_top_z, color=C_TRAY)
        ax.text(p.tray_y_min, p.midplate_z - 7, "tray: sheet, upstand with the groove (front fence translucent), end stops, pins", fontsize=8, color=C_TRAY, va="top")
        for y in {y for _, y in tray_pin_points(p)}:
            rect(ax, y - p.peg_y / 2 - 1.5, y + p.peg_y / 2 + 1.5, p.tray_top_z, p.tray_top_z + p.pin_head_thickness, color=C_PIN)
            rect(ax, y - p.peg_y / 2, y + p.peg_y / 2, p.tray_top_z - p.pin_shaft_length, p.tray_top_z, color=C_PIN)
    dim_y = foam_y - 10
    ax.annotate("", xy=(dim_y, p.midplate_z), xytext=(dim_y, p.outlet_z_min), arrowprops=dict(arrowstyle="<->", color="black"))
    ax.text(dim_y - 2, p.midplate_z / 2, f"midplate_gap {p.midplate_gap:g} (TODO)", fontsize=8, va="center", ha="right")
    ax.annotate("", xy=(dim_y, p.outlet_z_max), xytext=(dim_y, gpu_z0), arrowprops=dict(arrowstyle="<->", color="black"))
    ax.text(dim_y - 2, (p.outlet_z_max + gpu_z0) / 2, f"gpu_clearance {p.gpu_clearance:g} (TODO)", fontsize=8, va="center", ha="right")
    wall_in = p.shroud_wall_inner_y if p.mount_style == "card_clip" else p.cover_y_inner
    wall_out = p.shroud_wall_outer_y if p.mount_style == "card_clip" else p.cover_y_outer
    ax.annotate(f"side wall {wall_in - p.card_top_height:.1f} mm beyond the card top edges closes the side;\n"
                f"foam is {foam_y - wall_out:.0f} mm further out (side_clearance TODO)", xy=(wall_out, 30),
                xytext=(10, gpu_z1 + 6), fontsize=8, color=C_COVER, va="bottom",
                arrowprops=dict(arrowstyle="->", color=C_COVER, ls="--"))

    ax.set_xlim(-14, foam_y + 30)
    ax.set_ylim(p.midplate_z - 16, gpu_z1 + 22)
    ax.set_aspect("equal")
    ax.set_xlabel("Y: away from the motherboard, mm")
    ax.set_ylabel("Z: vertical, mm")
    closing = "shroud closing the plenum" if p.mount_style == "card_clip" else "cover and tray closing the plenum"
    ax.set_title(f"Outlet face seen from the fan side: one channel per usable slot, {closing}")
    ax.grid(alpha=0.2)
    path = OUT / f"outlet_view{SUFFIX}.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def tessellate(part, tolerance=0.2):
    verts, tris = part.tessellate(tolerance, 0.3)
    v = np.array([[q.X, q.Y, q.Z] for q in verts])
    mesh = trimesh.Trimesh(v, np.array(tris), process=False)
    mesh.fix_normals()
    return mesh


def box_mesh(x0, x1, y0, y1, z0, z1):
    box = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0))
    box.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return box


def material(color, alpha=1.0):
    rgb = matplotlib.colors.to_rgb(color)
    return pyrender.MetallicRoughnessMaterial(
        baseColorFactor=[*rgb, alpha], metallicFactor=0.0, roughnessFactor=0.7,
        alphaMode="BLEND" if alpha < 1 else "OPAQUE", doubleSided=True,
    )


def look_at(eye, target, up=(0.0, 0.0, 1.0)):
    eye, target = np.array(eye, float), np.array(target, float)
    f = target - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, np.array(up, float))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    pose = np.eye(4)
    pose[:3, 0], pose[:3, 1], pose[:3, 2], pose[:3, 3] = r, u, -f, eye
    return pose


def context_meshes(p):
    """Cards, GPU, motherboard, midplate and fan as (mesh, color, alpha)."""
    items = []
    z_pcb = [k * p.slot_pitch + p.channel_floor_below_pcb for k in range(p.slot_positions_covered)]
    for k, z in enumerate(z_pcb):
        card = CARD_LENGTHS.get(k)
        if card is None:
            continue
        length = card[1]
        items.append((box_mesh(-length, 0, p.connector_height, p.card_top_edge(k), z - PCB_THICKNESS, z), "#2d6a4f", 1.0))
        items.append((box_mesh(-length + 25, -45, 20, p.card_top_edge(k) - 8, z - PCB_THICKNESS - HEATSINK_DEPTH, z - PCB_THICKNESS), "#6b7280", 1.0))
        items.append((box_mesh(-length, 0, 0, p.connector_height, z - 3.5, z + 3.5), "#1f2937", 1.0))
    items.append((box_mesh(-330, 0, -1.6, 0, -40, 160), "#cbd5e0", 1.0))
    items.append((box_mesh(-330, 0, 0, 170, p.midplate_z - 1, p.midplate_z), "#4a5568", 1.0))
    fan_z0 = p.fan_center_z_eff - p.fan_size / 2
    items.append((box_mesh(p.fan_intake_x, p.fan_face_x, p.fan_center_y_eff - 40, p.fan_center_y_eff + 40, fan_z0, fan_z0 + p.fan_size), "#718096", 0.45))
    items.append((box_mesh(-p.gpu_length, 0, 0, 128, p.gpu_plane_z, p.gpu_pcb_z + GPU_BACKPLATE), "#a0aec0", 0.25))
    return items


def render_3d(p, parts, instances, name, eye, target, title, context=True, size=(1600, 1100)):
    scene = pyrender.Scene(bg_color=[1.0, 1.0, 1.0, 1.0], ambient_light=[0.35, 0.35, 0.35])
    colors = {"duct": C_DUCT, "tray": C_TRAY, "pin": C_PIN, "plug": C_PLUG, "gasket": C_GASKET, "cover": C_COVER, "shroud": C_SHROUD}
    colors.update({f"grip_slot{k + 1}": C_GRIP for k in range(p.slot_positions_covered)})
    for part_name, item in parts.items():
        for loc in instances.get(part_name, []):
            scene.add(pyrender.Mesh.from_trimesh(tessellate(item.part.moved(loc)), material=material(colors[part_name]), smooth=False))
    if context:
        for mesh, color, alpha in context_meshes(p):
            scene.add(pyrender.Mesh.from_trimesh(mesh, material=material(color, alpha), smooth=False))
    pose = look_at(eye, target)
    scene.add(pyrender.PerspectiveCamera(yfov=np.radians(32), aspectRatio=size[0] / size[1]), pose=pose)
    scene.add(pyrender.DirectionalLight(intensity=2.6), pose=pose)
    scene.add(pyrender.DirectionalLight(intensity=1.2), pose=look_at((-400, -200, 400), target))
    renderer = pyrender.OffscreenRenderer(*size)
    color, _ = renderer.render(scene)
    renderer.delete()
    image = Image.fromarray(color)
    canvas = Image.new("RGB", (size[0], size[1] + 50), "white")
    canvas.paste(image, (0, 50))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(matplotlib.font_manager.findfont("DejaVu Sans"), 22)
    draw.text((20, 14), title, fill="black", font=font)
    path = OUT / name.replace(".png", f"{SUFFIX}.png")
    canvas.save(path)
    return path


def main() -> int:
    global SUFFIX, CARD_LENGTHS
    p = load_params(Path(__file__).resolve().parent.parent / "configs" / "default.toml")
    if "--example-short-card" in sys.argv:
        import dataclasses
        p = dataclasses.replace(p, card_lengths=[106.5, 142.24, 167.64], card_pcb_heights=[57.0, 68.9, 68.9])
        assert p.validate() == []
        CARD_LENGTHS = {0: ("short X540 clone", 106.5), 1: ("MCX556N", 142.24), 2: ("Dell 57412", 167.64)}
        SUFFIX = "_short_card"
    parts = build_parts(p)
    instances = assembly_instances(p, parts)
    target = (-100, 50, 25)
    views = [
        side_section(p),
        outlet_view(p),
        render_3d(p, parts, instances, "view_from_brackets.png", (230, 25, 150), (-70, 45, 25),
                  "From the bracket end, looking into the open exhaust end: cards (green) inside the shroud (ochre), pockets and grips (purple) on the far wall"),
        render_3d(p, parts, instances, "view_from_front.png", (-470, 300, 170), target,
                  "From the case front: fan (translucent grey) on the duct flange, duct (blue) converging into the shroud under the GPU"),
        render_3d(p, parts, instances, "view_parts_only.png", (-60, -330, 110), (-95, 45, 28),
                  "Parts only, seen from the motherboard side: wall pockets with the three TPU grips, bottom plate, stub, flange and duct", context=False),
    ]
    for path in views:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
