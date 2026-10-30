"""Geometry checks against the built parts and their exported meshes."""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest
import trimesh
from build123d import Location, Part

from duct.build import build_parts
from duct.export import PrintPart, export_part
from duct.fan import axial_cylinder, fan_hole_centers, fan_screw_bores, fan_screw_tubes
from duct.mounts import foot_pin_points, nearest_grid_point
from duct.outlet import box_between
from duct.params import Params, load_params
from duct.transition import cavity, vane_planes
from duct.tray import tray_pin_points

CONFIG = Path(__file__).resolve().parent.parent / "configs" / "default.toml"
TOL = 0.2


@pytest.fixture(scope="module", params=["card_clip", "case"])
def params(request) -> Params:
    base = load_params(CONFIG)
    overrides = dict(mount_style=request.param)
    if request.param == "case":
        # The case mount's tray and 80 mm duct no longer fit this machine (78 mm under the GPU, bottom plate
        # 8 mm lower since the 2026-10-18 test fit). Keep the code tested at the card spacing it was built for.
        overrides["channel_floor_below_pcb"] = 16.0
    variant = dataclasses.replace(base, **overrides)
    assert variant.validate() == [], variant.validate()
    return variant


@pytest.fixture(scope="module")
def parts(params: Params) -> dict[str, PrintPart]:
    return build_parts(params)


@pytest.fixture(scope="module")
def meshes(params: Params, parts: dict[str, PrintPart], tmp_path_factory) -> dict[str, trimesh.Trimesh]:
    out_dir = tmp_path_factory.mktemp("out")
    result = {}
    for name, item in parts.items():
        written = export_part(item, params, out_dir)
        result[name] = trimesh.load(written["stl"], force="mesh")
    return result


def probe_volume(part: Part, x0, x1, y0, y1, z0, z1) -> float:
    return (part & box_between(x0, x1, y0, y1, z0, z1)).volume


def vane_at_x(params: Params, z_fan: float, z_out: float, x: float) -> tuple[float, float]:
    """(centre z, vertical thickness) of a tilted vane at X."""
    slope = (z_out - z_fan) / params.transition_length_eff
    centre = z_out + (x - params.outlet_x) * slope
    return centre, params.vane_thickness * math.sqrt(1 + slope * slope)


# --- meshes ---

def test_meshes_watertight_with_volume(meshes):
    for name, mesh in meshes.items():
        assert mesh.is_watertight, name
        assert mesh.volume > 0, name


def test_each_part_is_one_solid(parts):
    for name, item in parts.items():
        assert len(item.part.solids()) == 1, name


# --- outlet ---

def test_outlet_spans_slot_count_and_card_zone(params, parts):
    if params.mount_style != "case":
        pytest.skip("separate duct: case mount only")
    duct = parts["duct"].part
    x1 = params.outlet_x - 0.5
    x0 = x1 - 0.5
    y0, y1 = params.outlet_y_min, params.outlet_y_max
    z0, z1 = params.outlet_z_min, params.outlet_z_max
    assert (y1 - y0) == pytest.approx(params.card_zone_height, abs=TOL)
    assert (z1 - z0) == pytest.approx(params.slot_positions_covered * params.slot_pitch - params.top_channel_trim, abs=TOL)
    assert params.top_channel_trim < 5.0
    # Material just outside each wall of the opening.
    assert probe_volume(duct, x0, x1, y0 - 1, y0 - TOL, z0 + 5, z1 - 5) > 0
    assert probe_volume(duct, x0, x1, y1 + TOL, y1 + 1, z0 + 5, z1 - 5) > 0
    assert probe_volume(duct, x0, x1, y0 + 5, y1 - 5, z0 - 1, z0 - TOL) > 0
    assert probe_volume(duct, x0, x1, y0 + 5, y1 - 5, z1 + TOL, z1 + 1) > 0
    # Only vane material inside the opening.
    inside = probe_volume(duct, x0, x1, y0 + TOL, y1 - TOL, z0 + TOL, z1 - TOL)
    vertical = [vane_at_x(params, z_fan, z_out, (x0 + x1) / 2)[1] for z_fan, z_out in vane_planes(params)]
    expected = sum(vertical) * (y1 - y0 - 2 * TOL) * (x1 - x0)
    # Plus the fan screw tubes where they cross the opening's corners.
    tubes = fan_screw_tubes(params) - fan_screw_bores(params)
    expected += probe_volume(tubes, x0, x1, y0 + TOL, y1 - TOL, z0 + TOL, z1 - TOL)
    assert inside == pytest.approx(expected, rel=0.02)


def test_one_channel_per_slot_with_vanes_on_grid(params, parts):
    if params.mount_style != "case":
        pytest.skip("separate duct: case mount only")
    duct = parts["duct"].part
    x1 = params.outlet_x - 0.5
    x0 = x1 - 0.5
    y_mid = (params.outlet_y_min + params.outlet_y_max) / 2
    planes = vane_planes(params)
    assert len(planes) == params.slot_positions_covered - 1
    for (z_fan, z_out), z_grid in zip(planes, params.channel_boundaries_z[1:-1]):
        assert z_out == pytest.approx(z_grid)
        # The vane passes through the grid line at the outlet face.
        at_face = probe_volume(duct, params.outlet_x - 0.1, params.outlet_x, y_mid - 5, y_mid + 5, z_grid - 0.1, z_grid + 0.1)
        assert at_face == pytest.approx(0.1 * 10 * 0.2, rel=0.05), f"vane missing at z={z_grid}"
        centre, thick = vane_at_x(params, z_fan, z_out, (x0 + x1) / 2)
        slope = abs(z_out - z_fan) / params.transition_length_eff
        half = thick / 2 + slope * (x1 - x0) / 2
        vane = probe_volume(duct, x0, x1, y_mid - 5, y_mid + 5, centre - half, centre + half)
        assert vane == pytest.approx(10 * thick * (x1 - x0), rel=0.02), f"vane at z={z_grid}"
        gap_lo = probe_volume(duct, x0, x1, y_mid - 5, y_mid + 5, centre - half - 2, centre - half - TOL)
        gap_hi = probe_volume(duct, x0, x1, y_mid - 5, y_mid + 5, centre + half + TOL, centre + half + 2)
        assert gap_lo == 0 and gap_hi == 0, f"vane at z={z_grid} thicker than configured"
    for k in range(params.slot_positions_covered):
        z = params.outlet_z_min + (k + 0.5) * params.slot_pitch
        assert probe_volume(duct, x0, x1, y_mid - 5, y_mid + 5, z - 5, z + 5) == 0, f"channel {k} obstructed"


# --- clearances ---

def test_duct_stays_past_outlet_plane(params, parts):
    if params.mount_style != "case":
        pytest.skip("separate duct: case mount only")
    bb = parts["duct"].part.bounding_box()
    assert bb.max.X <= -params.outlet_offset_from_bracket + 1e-6


def test_duct_below_gpu_clearance_plane(params, parts):
    limit = params.gpu_plane_z - params.gpu_top_clearance + 1e-6
    for name in ("duct", "cover", "shroud"):
        if name in parts:
            assert parts[name].part.bounding_box().max.Z <= limit, name


def test_duct_clear_of_motherboard_and_midplate(params, parts):
    if params.mount_style != "case":
        pytest.skip("separate duct: case mount only")
    bb = parts["duct"].part.bounding_box()
    assert bb.min.Y > 0
    assert bb.min.Z >= params.midplate_z - 1e-6


def test_expansion_half_angle(params):
    if params.mount_style != "case":
        pytest.skip("separate duct: case mount only")
    assert params.angle_violations() == []


def test_shroud_pockets_and_grips(params, parts):
    if params.mount_style != "card_clip":
        pytest.skip("card-clip mount only")
    shroud = parts["shroud"].part
    bb = shroud.bounding_box()
    assert bb.min.X == pytest.approx(params.shroud_x_min, abs=1e-6)
    assert bb.max.X <= 1e-6, "nothing past the bracket plane"
    # The exhaust gap stays open across the card zone: only the arms (beyond the wall) reach into it.
    assert probe_volume(shroud, -params.exhaust_gap + 0.01, 10, -50, params.shroud_wall_inner_y - 0.01, -50, 200) == 0
    assert bb.max.Z <= params.gpu_plane_z - params.gpu_top_clearance + 1e-6
    # No lid beyond the stub (outside the pocket zone): the top card's PCB is the roof.
    assert probe_volume(shroud, params.stub_x_max + 2, bb.max.X, params.cover_y_min + 0.1, params.pocket_inner_y_min - 0.1,
                        params.outlet_z_max + 0.1, params.shroud_top_z + 5) == 0
    # Stub bridges from the tail wall to the top card's tail.
    assert probe_volume(shroud, bb.min.X + params.tail_wall_thickness + 0.1, params.stub_x_max - 0.1,
                        params.cover_y_min + 1, params.shroud_wall_inner_y - 1,
                        params.outlet_z_max + 0.1, params.outlet_z_max + params.wall_thickness - 0.1) > 0
    # Plates stay clear of the slot connector housings.
    body = shroud & box_between(params.shroud_x_min + params.tail_wall_thickness + 0.1, bb.max.X, -50, 200, -50, 200)
    assert body.bounding_box().min.Y >= params.connector_height
    y_wall = params.shroud_wall_inner_y
    for slot in range(params.slot_positions_covered):
        pz0, pz1 = params.pocket_z_range(slot)
        gx0, gx1 = params.grip_x_range(slot)
        grip = parts[f"grip_slot{slot + 1}"].part
        gb = grip.bounding_box()
        assert gb.size.X == pytest.approx(params.grip_length(slot), abs=0.01)
        assert gb.size.Y == pytest.approx(params.grip_key_width, abs=0.01)
        assert gb.size.Z == pytest.approx(params.grip_height(slot), abs=0.01)
        channel = grip & box_between(-gb.size.X / 2 - 1, gb.size.X / 2 + 1, -params.grip_slot_width / 2 + 0.05,
                                     params.grip_slot_width / 2 - 0.05, params.grip_back(slot) + 0.05, params.grip_height(slot) + 1)
        assert channel.volume == 0, "grip channel is not open"
        # The pocket is empty where the whole grip sits, and ribs stand on both sides of it.
        back = params.grip_back_y(slot)
        top = params.card_top_edge(slot)
        assert probe_volume(shroud, gx0, gx1, top - params.grip_engagement, back - 0.05, pz0 + 0.05, pz1 - 0.05) == 0
        for rz0, rz1 in params.pocket_rib_z_ranges(slot):
            assert probe_volume(shroud, gx0, gx1, params.pocket_inner_y(slot) + 0.1, y_wall - 0.1, rz0 + 0.1, rz1 - 0.1) > 0
        # The card edge itself passes under the pocket untouched.
        pcb = params.pcb_z(slot)
        assert probe_volume(shroud, gx0 - 5, gx1 + 5, min(params.pocket_inner_y(slot), top) - 1, back - 0.05,
                            pcb - params.pcb_thickness / 2, pcb + params.pcb_thickness / 2) == 0


def test_shroud_independent_of_card_heights(params, parts):
    if params.mount_style != "card_clip" or params.grip_fill != "grip":
        pytest.skip("card-clip mount with grip_fill = grip only")
    from duct.shroud import card_shroud
    shorter = dataclasses.replace(params, card_pcb_heights=[h - 6.0 for h in params.card_pcb_heights])
    assert shorter.validate() == []
    other = card_shroud(shorter)
    assert other.volume == pytest.approx(parts["shroud"].part.volume, rel=1e-6)
    assert (other - parts["shroud"].part).volume == pytest.approx(0, abs=1e-6)


def test_grips_held_by_dovetails(params, parts):
    if params.mount_style != "card_clip":
        pytest.skip("card-clip mount only")
    from duct.build import assembly_instances
    instances = assembly_instances(params, parts)
    shroud = parts["shroud"].part
    key_half, neck_half = params.grip_key_width / 2, params.grip_outer_width / 2
    assert key_half - neck_half == pytest.approx(params.dovetail_depth * math.tan(math.radians(params.dovetail_angle)))
    for slot in range(params.slot_positions_covered):
        grip = parts[f"grip_slot{slot + 1}"].part
        length = params.grip_length(slot)
        # The key is widest on the back face the grip prints on and narrows to the neck over dovetail_depth.
        flank = (neck_half + key_half) / 2
        assert probe_volume(grip, -length / 2, length / 2, flank - 0.05, flank + 0.05, 0, 0.1) > 0
        assert probe_volume(grip, -length / 2, length / 2, neck_half + 0.05, key_half,
                            params.dovetail_depth + 0.05, params.grip_height(slot)) == 0
        placed = grip.moved(instances[f"grip_slot{slot + 1}"][0])
        # Pulling the grip away from the wall toward the card runs its key into the groove's undercut.
        pull = params.pocket_clearance + 0.5
        assert (placed.moved(Location((0, -pull, 0))) & shroud).volume > 0, f"grip {slot + 1} pulls out of its groove"
        # Along the groove it slides freely between its place and the shroud's open bracket end.
        gx0, gx1 = params.grip_x_range(slot)
        half_out = params.shroud_x_max - (gx0 + gx1) / 2
        for dx in (half_out / 2, half_out):
            assert (placed.moved(Location((dx, 0, 0))) & shroud).volume == 0, f"grip {slot + 1} binds at dx={dx:.1f}"


def test_grips_placed_on_card_edges(params, parts):
    if params.mount_style != "card_clip":
        pytest.skip("card-clip mount only")
    from duct.build import assembly_instances
    instances = assembly_instances(params, parts)
    shroud = parts["shroud"].part
    for slot in range(params.slot_positions_covered):
        placed = parts[f"grip_slot{slot + 1}"].part.moved(instances[f"grip_slot{slot + 1}"][0])
        gb = placed.bounding_box()
        assert gb.max.Y == pytest.approx(params.grip_back_y(slot), abs=0.01)
        assert gb.min.Y == pytest.approx(params.card_top_edge(slot) - params.grip_engagement, abs=0.01)
        assert (gb.min.Z + gb.max.Z) / 2 == pytest.approx(params.pcb_z(slot), abs=0.01)
        assert (placed & shroud).volume == 0, f"grip {slot + 1} intersects the shroud"


def test_tail_fan_mount(params, parts):
    if params.mount_style != "card_clip":
        pytest.skip("card-clip mount only")
    shroud = parts["shroud"].part
    x0, x1 = params.shroud_x_min, params.shroud_x_min + params.tail_wall_thickness
    cy, cz, half = params.tail_fan_center_y_eff, params.tail_fan_center_z_eff, params.tail_fan_size / 2
    # The fan's 60 x 60 frame lies flat on the end wall: wall material all round its outline.
    wy0, wy1 = params.tail_wall_y_range
    wz0, wz1 = params.tail_wall_z_range
    assert wy0 <= cy - half and cy + half <= wy1 and wz0 <= cz - half and cz + half <= wz1
    # Nothing outside the shroud's cross-section: no flange beyond the walls.
    bb = shroud.bounding_box()
    assert bb.min.X == pytest.approx(x0, abs=1e-6)
    # Fan opening clear, wall solid around it.
    r = params.tail_fan_opening / 2 / math.sqrt(2) - 0.1
    assert probe_volume(shroud, x0 - 0.5, x1 + 0.5, cy - r, cy + r, cz - r, cz + r) == 0
    assert probe_volume(shroud, x0, x1, cy + params.tail_fan_opening / 2 + 0.3, cy + half, cz - 1, cz + 1) > 0
    # Four fan screw holes on the hole pattern, with wall around each.
    points = params.tail_fan_hole_points()
    ys = sorted({y for y, _ in points})
    assert ys[1] - ys[0] == pytest.approx(params.tail_fan_hole_spacing)
    rc = params.fan_screw_clearance / 2 / math.sqrt(2) - 0.05
    ring = params.fan_screw_clearance / 2 + 0.3
    for y, z in points:
        assert probe_volume(shroud, x0 - 0.5, x1 + 0.5, y - rc, y + rc, z - rc, z + rc) == 0
        assert probe_volume(shroud, x0, x1, y - 0.5, y + 0.5, z + ring, z + ring + 1) > 0
    # Clear of the GPU and the midplate, and inside the free length past the cards.
    assert cz + half <= params.gpu_plane_z - params.fan_gpu_clearance + 1e-6
    assert cz - half >= params.midplate_z - 1e-6
    assert -params.tail_fan_intake_x <= params.longest_card_length + params.free_length_past_cards + 1e-6
    # The tail wall stays clear of the longest card's tail.
    assert x1 <= -params.longest_card_length - params.tail_clearance + 1e-6


def test_bracket_tab(params, parts):
    if params.mount_style != "card_clip":
        pytest.skip("card-clip mount only")
    shroud = parts["shroud"].part
    tx0, tx1 = params.bracket_tab_x_range
    y0, y1 = params.bracket_tab_y, params.bracket_tab_y + params.bracket_tab_thickness
    rc = params.bracket_screw_clearance / 2 / math.sqrt(2) - 0.05
    x = params.bracket_screw_x
    w = params.bracket_arm_width
    zs = params.bracket_screw_points()
    for z in zs:
        # An ear with a clearance hole on every covered slot's bracket screw, material around the hole.
        assert probe_volume(shroud, x - rc, x + rc, y0 - 0.5, y1 + 0.5, z - rc, z + rc) == 0
        assert probe_volume(shroud, tx0 + 0.1, x - params.bracket_screw_clearance / 2 - 0.1, y0 + 0.1, y1 - 0.1, z - 1, z + 1) > 0
        # Nothing under the ear, where the metal bracket tab and the slot rail sit.
        assert probe_volume(shroud, tx0 + 0.1, tx1, params.shroud_wall_outer_y + 0.1, y0 - 0.1, z - w / 2, z + w / 2) == 0
        # The arm carrying it crosses the exhaust gap beyond the wall.
        assert probe_volume(shroud, params.shroud_x_max + 0.5, tx0 - 0.5, params.shroud_wall_inner_y + 0.1, y0, z - w / 2 + 0.1, z + w / 2 - 0.1) > 0
        # A ridge on each long edge: along the ear up to the screw head and down the rib's flank to the wall.
        rw, h = params.bracket_ridge_width, params.bracket_ridge_height
        x_root, y_out = params.bracket_arm_root_x, params.shroud_wall_outer_y
        x_mid = (x_root + tx0) / 2
        y_edge = y_out + (y1 - y_out) * (x_mid - x_root) / (tx0 - x_root)
        for zr in (z - w / 2, z + w / 2 - rw):
            assert probe_volume(shroud, tx0 + 0.1, params.bracket_ridge_end_x - 0.1, y1 + 0.1, y1 + h - 0.1, zr + 0.1, zr + rw - 0.1) > 0
            assert probe_volume(shroud, x_mid - 0.1, x_mid + 0.1, y_edge + 0.2, y_edge + h - 0.2, zr + 0.1, zr + rw - 0.1) > 0
        assert probe_volume(shroud, x_mid - 0.1, x_mid + 0.1, y_edge + 0.2, y_edge + h - 0.2, z - w / 2 + rw + 0.1, z + w / 2 - rw - 0.1) == 0
        # The screw head's seat on the ear stays clear of the ridges.
        head = params.bracket_screw_head_clearance / 2 / math.sqrt(2)
        assert probe_volume(shroud, x - head, x + head, y1 + 0.01, y1 + h + 1, z - head, z + head) == 0
    # Between the arms the exhaust gap is open all the way out past the bracket tabs.
    for za, zb in zip(zs, zs[1:]):
        assert probe_volume(shroud, params.shroud_x_max + 0.5, 0, params.shroud_wall_inner_y, y1 + 1, za + w / 2 + 0.1, zb - w / 2 - 0.1) == 0


def test_side_cover_respects_exhaust_gap(params, parts):
    if params.mount_style != "case" or not params.side_cover:
        pytest.skip("case mount with a side cover only")
    bb = parts["cover"].part.bounding_box()
    assert bb.max.X <= -params.exhaust_gap
    assert bb.min.X >= params.outlet_x + params.outlet_gasket_thickness - 1e-6
    assert bb.min.Y > params.connector_height
    assert bb.max.Y <= params.frame_bounds()[1] + 1e-6
    assert bb.min.Z == pytest.approx(params.tray_top_z, abs=1e-6)


# --- fan ---

def test_fan_hole_spacing(params, parts):
    if params.mount_style != "case":
        pytest.skip("separate duct: case mount only")
    duct = parts["duct"].part
    assert params.fan_hole_spacing == pytest.approx(71.5)
    face, seat = params.fan_face_x, params.fan_screw_seat
    r_clear = (params.fan_screw_clearance / 2) / math.sqrt(2) - 0.05
    r_head = (params.fan_screw_head_clearance / 2) / math.sqrt(2) - 0.05
    air = cavity(params) - duct
    for dy, dz in fan_hole_centers(params):
        y, z = params.fan_center_y_eff + dy, params.fan_center_z_eff + dz
        # Screw from the duct side: clearance hole through the seat, head bore from the seat out
        # through the outlet face so a driver reaches it.
        assert probe_volume(duct, face - 1, face + seat + 0.2, y - r_clear, y + r_clear, z - r_clear, z + r_clear) == 0
        assert probe_volume(duct, face + seat + 0.2, params.outlet_x + 0.5, y - r_head, y + r_head, z - r_head, z + r_head) == 0
        # The seat the head bears on, on the pad side of the hole.
        sign = -1 if dy > 0 else 1
        a, b = y + sign * (params.fan_screw_clearance / 2 + 0.2), y + sign * (params.fan_screw_head_clearance / 2 - 0.2)
        assert probe_volume(duct, face + 0.2, face + seat - 0.2, min(a, b), max(a, b), z - 0.5, z + 0.5) > 0, "no screw seat"
        # The tube wall all round the head bore keeps it out of the air passage.
        r0 = params.fan_screw_head_clearance / 2
        wall = axial_cylinder(r0 + params.fan_screw_tube_wall - 0.2, face + seat, params.outlet_x - 0.5, y, z)
        wall -= axial_cylinder(r0 + 0.2, face + seat - 1, params.outlet_x, y, z)
        assert (air & wall).volume == pytest.approx(0, abs=1e-3), "fan screw bore opens into the duct"
        assert (wall - duct).volume == pytest.approx(0, abs=1e-3), "fan screw tube wall incomplete"
    ys = sorted({dy for dy, _ in fan_hole_centers(params)})
    assert ys[1] - ys[0] == pytest.approx(71.5)


# --- tray and pins ---

def test_pins_match_perforations(params, parts):
    if params.mount_style != "case":
        pytest.skip("case mount only")
    shaft = parts["pin"].part & box_between(-10, 10, -10, 10, params.pin_head_thickness + 0.5, params.pin_head_thickness + 1.0)
    size = shaft.bounding_box().size
    if params.hole_pattern == "slots":
        assert size.X == pytest.approx(params.slot_length - params.peg_clearance, abs=0.01)
        assert size.Y == pytest.approx(params.slot_width - params.peg_clearance, abs=0.01)
        hole_x, hole_y = size.X + params.pin_hole_clearance, size.Y + params.pin_hole_clearance
    else:
        assert size.X == pytest.approx(params.hole_diameter - params.peg_clearance, abs=0.01)
        hole_x = hole_y = size.X + params.pin_hole_clearance
    tray = parts["tray"].part
    points = tray_pin_points(params)
    assert len(points) >= 2
    for x, y in points:
        assert nearest_grid_point(params, x, y) == (x, y)
        assert not params.overlaps_cutout(x - 1, x + 1, y - 1, y + 1)
        inside = probe_volume(tray, x - hole_x / 2 + 0.1, x + hole_x / 2 - 0.1, y - hole_y / 2 + 0.1, y + hole_y / 2 - 0.1,
                              params.midplate_z - 1, params.tray_top_z + 1)
        assert inside == 0
        around = probe_volume(tray, x - hole_x, x + hole_x, y - hole_y, y + hole_y, params.midplate_z - 1, params.tray_top_z + 1)
        assert around > 0
    if params.fan_foot:
        foot = foot_pin_points(params)
        assert len(foot) >= 1
        for x, y in foot:
            assert nearest_grid_point(params, x, y) == (x, y)


def test_tray_covers_card_zone_only(params, parts):
    if params.mount_style != "case":
        pytest.skip("case mount only")
    tray = parts["tray"].part
    bb = tray.bounding_box()
    assert bb.max.X == pytest.approx(-params.exhaust_gap, abs=TOL)
    assert bb.min.X == pytest.approx(params.upstand_x_min, abs=TOL)
    assert params.outlet_x - bb.min.X <= params.gasket_lip_thickness + params.mount_groove_clearance + params.wall_thickness + TOL
    # Solid sheet from the outlet plane to the exhaust gap.
    sheet = probe_volume(tray, params.outlet_x, -params.exhaust_gap, params.tray_y_min, params.tray_y_max,
                         params.midplate_z, params.tray_top_z)
    area = (-params.exhaust_gap - params.outlet_x) * (params.tray_y_max - params.tray_y_min)
    assert sheet >= 0.97 * area * params.tray_thickness


def test_tray_and_pin_heads_fit_under_bottom_slot(params, parts):
    if params.mount_style != "case":
        pytest.skip("case mount only")
    bb = parts["tray"].part.bounding_box()
    assert bb.min.Z >= params.midplate_z - 1e-6
    assert params.tray_top_z + params.pin_head_thickness < params.outlet_z_min
    assert bb.max.Z < params.duct_bottom_z
    assert params.pin_shaft_length - params.tray_thickness - params.sheet_thickness < params.under_midplate_gap


# --- printability ---

def sampled_min_thickness(mesh: trimesh.Trimesh, samples: int = 1500, seed: int = 0) -> float:
    """Smallest distance between opposite, parallel faces found by ray casting from sampled points."""
    points, faces = trimesh.sample.sample_surface(mesh, samples, seed=seed)
    normals = mesh.face_normals[faces]
    origins = points - normals * 1e-3
    locations, ray_ids, tri_ids = mesh.ray.intersects_location(origins, -normals, multiple_hits=False)
    best = np.inf
    for loc, ray_id, tri_id in zip(locations, ray_ids, tri_ids):
        if np.dot(mesh.face_normals[tri_id], normals[ray_id]) > -0.9:
            continue
        best = min(best, float(np.linalg.norm(loc - origins[ray_id])))
    return best


def test_minimum_wall_thickness(params, parts, meshes):
    for name, mesh in meshes.items():
        is_tpu = parts[name].material.startswith("TPU")
        limit = params.tpu_min_wall_thickness if is_tpu else params.min_wall_thickness
        thinnest = sampled_min_thickness(mesh)
        assert thinnest >= limit - 0.05, f"{name}: {thinnest:.2f} mm"


def test_parts_fit_bed(params, parts):
    limit_x = params.bed_x - 2 * params.bed_margin
    limit_y = params.bed_y - 2 * params.bed_margin
    for name, item in parts.items():
        bb = item.oriented(params).bounding_box()
        assert bb.size.X <= limit_x and bb.size.Y <= limit_y and bb.size.Z <= params.bed_z, name
        assert bb.min.Z == pytest.approx(0, abs=1e-6), name
