"""Geometry checks against the built parts and their exported meshes."""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest
import trimesh
from build123d import Part

from duct.build import build_parts
from duct.export import PrintPart, export_part
from duct.fan import fan_hole_centers
from duct.mounts import foot_pin_points, nearest_grid_point
from duct.outlet import box_between
from duct.params import Params, load_params
from duct.transition import vane_planes
from duct.tray import tray_pin_points

CONFIG = Path(__file__).resolve().parent.parent / "configs" / "default.toml"
TOL = 0.2


@pytest.fixture(scope="module", params=["card_clip", "case"])
def params(request) -> Params:
    base = load_params(CONFIG)
    variant = dataclasses.replace(base, mount_style=request.param)
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
    assert inside == pytest.approx(expected, rel=0.02)


def test_one_channel_per_slot_with_vanes_on_grid(params, parts):
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
    bb = parts["duct"].part.bounding_box()
    assert bb.max.X <= -params.outlet_offset_from_bracket + 1e-6


def test_duct_below_gpu_clearance_plane(params, parts):
    limit = params.gpu_plane_z - params.gpu_top_clearance + 1e-6
    for name in ("duct", "cover", "shroud"):
        if name in parts:
            assert parts[name].part.bounding_box().max.Z <= limit, name


def test_duct_clear_of_motherboard_and_midplate(params, parts):
    bb = parts["duct"].part.bounding_box()
    assert bb.min.Y > 0
    assert bb.min.Z >= params.midplate_z - 1e-6


def test_expansion_half_angle(params):
    assert params.angle_violations() == []


def test_shroud_pockets_and_grips(params, parts):
    if params.mount_style != "card_clip":
        pytest.skip("card-clip mount only")
    shroud = parts["shroud"].part
    bb = shroud.bounding_box()
    assert bb.min.X == pytest.approx(params.shroud_x_min, abs=1e-6)
    assert bb.max.X <= -params.exhaust_gap + 1e-6
    assert bb.max.Z <= params.gpu_plane_z - params.gpu_top_clearance + 1e-6
    # No lid beyond the stub (outside the pocket zone): the top card's PCB is the roof.
    assert probe_volume(shroud, params.stub_x_max + 2, bb.max.X, params.cover_y_min + 0.1, params.pocket_inner_y_min - 0.1,
                        params.outlet_z_max + 0.1, params.shroud_top_z + 5) == 0
    # Stub bridges from the flange to the top card's tail.
    assert probe_volume(shroud, bb.min.X + params.gasket_lip_thickness + 0.1, params.stub_x_max - 0.1,
                        params.cover_y_min + 1, params.shroud_wall_inner_y - 1,
                        params.outlet_z_max + 0.1, params.outlet_z_max + params.wall_thickness - 0.1) > 0
    # Plates stay clear of the slot connector housings.
    body = shroud & box_between(params.shroud_x_min + params.gasket_lip_thickness + 0.1, bb.max.X, -50, 200, -50, 200)
    assert body.bounding_box().min.Y >= params.connector_height
    y_wall = params.shroud_wall_inner_y
    for slot in range(params.slot_positions_covered):
        pz0, pz1 = params.pocket_z_range(slot)
        gx0, gx1 = params.grip_x_range(slot)
        grip = parts[f"grip_slot{slot + 1}"].part
        gb = grip.bounding_box()
        assert gb.size.X == pytest.approx(params.grip_length(slot), abs=0.01)
        assert gb.size.Y == pytest.approx(params.grip_outer_width, abs=0.01)
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
    # Flange matches the duct's outlet frame outline so the gasket seals both.
    y0, y1, z0, z1 = params.frame_bounds()
    x_f0, x_f1 = params.shroud_x_min - 1, params.shroud_x_min + params.gasket_lip_thickness
    fb = (shroud & box_between(x_f0, x_f1, -50, 200, -50, 200)).bounding_box()
    assert (fb.min.Y, fb.max.Y, fb.min.Z) == pytest.approx((y0, params.joint_side_y_outer, params.joint_ear_z_bottom), abs=0.01)
    # Height measured away from the wall, whose pocket ribs rise above the flange.
    top = (shroud & box_between(x_f0, x_f1, -50, params.pocket_inner_y_min - 0.1, -50, 200)).bounding_box()
    assert top.max.Z == pytest.approx(z1, abs=0.01)


def test_shroud_independent_of_card_heights(params, parts):
    if params.mount_style != "card_clip" or params.grip_fill != "grip":
        pytest.skip("card-clip mount with grip_fill = grip only")
    from duct.shroud import card_shroud
    shorter = dataclasses.replace(params, card_pcb_heights=[h - 6.0 for h in params.card_pcb_heights])
    assert shorter.validate() == []
    other = card_shroud(shorter)
    assert other.volume == pytest.approx(parts["shroud"].part.volume, rel=1e-6)
    assert (other - parts["shroud"].part).volume == pytest.approx(0, abs=1e-6)


def test_grip_screws_line_up(params, parts):
    if params.mount_style != "card_clip":
        pytest.skip("card-clip mount only")
    from duct.build import assembly_instances
    instances = assembly_instances(params, parts)
    shroud = parts["shroud"].part
    # Square probes inscribed in the round holes (half-diagonal under the radius).
    r = (params.grip_screw_diameter / 2 + 0.15) / math.sqrt(2) - 0.05
    pr = params.grip_screw_pilot / 2 / math.sqrt(2) - 0.05
    for slot in range(params.slot_positions_covered):
        placed = parts[f"grip_slot{slot + 1}"].part.moved(instances[f"grip_slot{slot + 1}"][0])
        z = params.pcb_z(slot)
        for x in params.grip_screw_x:
            # Clearance hole through the wall at every position, whatever card is fitted.
            assert probe_volume(shroud, x - r, x + r, params.shroud_wall_inner_y - 0.5, params.shroud_wall_outer_y + 0.5,
                                z - r, z + r) == 0, f"wall hole missing at x={x} slot {slot + 1}"
        assert len(params.grip_screw_positions(slot)) >= 2
        for x in params.grip_screw_positions(slot):
            # Pilot in the grip back, open at the wall side, stopping min_wall_thickness short of the channel.
            back_y = params.grip_back_y(slot)
            floor_y = back_y - params.grip_back(slot) + params.tpu_min_wall_thickness
            assert probe_volume(placed, x - pr, x + pr, floor_y + 0.1, back_y + 0.5, z - pr, z + pr) == 0, \
                f"pilot missing at x={x} slot {slot + 1}"
            assert probe_volume(placed, x - pr, x + pr, floor_y - params.tpu_min_wall_thickness + 0.05, floor_y - 0.05,
                                z - pr, z + pr) > 0, "pilot breaks through toward the PCB"


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


def test_joint_screws_line_up(params, parts):
    if params.mount_style != "card_clip":
        pytest.skip("card-clip mount only")
    from duct.outlet import joint_screw_points
    duct, shroud, gasket = parts["duct"].part, parts["shroud"].part, parts["gasket"].part
    r_clear = (params.joint_screw_clearance / 2) / math.sqrt(2) - 0.05
    r_pilot = (params.joint_screw_pilot / 2) / math.sqrt(2) - 0.05
    points = joint_screw_points(params)
    assert len(points) == params.joint_ear_count + len(params.joint_side_screw_fractions)
    x0 = params.shroud_x_min
    ring_in, ring_out = params.joint_screw_clearance / 2 + 0.3, params.joint_screw_clearance / 2 + 1.5
    for y, z in points:
        # Fan-screw pilot through the duct's thick bar; clearance through the gasket and the shroud's thin bar.
        assert probe_volume(duct, params.outlet_x - params.joint_ear_thickness + 0.2, params.outlet_x + 0.5, y - r_pilot, y + r_pilot, z - r_pilot, z + r_pilot) == 0
        assert probe_volume(gasket, params.outlet_x - 0.5, params.outlet_x + params.outlet_gasket_thickness + 0.5, y - r_clear, y + r_clear, z - r_clear, z + r_clear) == 0
        assert probe_volume(shroud, x0 - 0.5, x0 + params.gasket_lip_thickness + 0.5, y - r_clear, y + r_clear, z - r_clear, z + r_clear) == 0
        # Bar material above and below each hole on all three parts.
        for part, (px0, px1) in ((duct, (params.outlet_x - params.joint_ear_thickness, params.outlet_x)),
                                 (gasket, (params.outlet_x, x0)), (shroud, (x0, x0 + params.gasket_lip_thickness))):
            assert probe_volume(part, px0, px1, y - 1, y + 1, z + ring_in, z + ring_out) > 0
            assert probe_volume(part, px0, px1, y - 1, y + 1, z - ring_out, z - ring_in) > 0
    assert (shroud & duct).volume == pytest.approx(0, abs=1e-6), "shroud intersects the duct"


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
    duct = parts["duct"].part
    assert params.fan_hole_spacing == pytest.approx(71.5)
    r = (params.fan_insert_bore / 2) / math.sqrt(2) - 0.05
    x0 = params.fan_face_x - 1
    x1 = params.fan_face_x + params.fan_insert_depth - 0.2
    px0, px1 = params.fan_face_x + 0.5, params.fan_face_x + params.fan_flange_thickness - 0.5
    for dy, dz in fan_hole_centers(params):
        y, z = params.fan_center_y_eff + dy, params.fan_center_z_eff + dz
        # Insert bore open from the fan face to its full depth.
        assert probe_volume(duct, x0, x1, y - r, y + r, z - r, z + r) == 0, "insert bore blocked"
        # Corner pad material on the opening side of the bore, within the flange thickness.
        sign = -1 if dy > 0 else 1
        ring_in = params.fan_insert_bore / 2 + 0.2
        ring_out = ring_in + 1.5
        pad = probe_volume(duct, px0, px1, min(y + sign * ring_in, y + sign * ring_out), max(y + sign * ring_in, y + sign * ring_out), z - 1, z + 1)
        assert pad > 0, "corner pad missing inside the insert bore"
        # Bore closed at the bottom: flange material past the insert depth.
        bottom = probe_volume(duct, params.fan_face_x + params.fan_insert_depth + 0.2,
                              params.fan_face_x + params.fan_flange_thickness - 0.2, y - 1, y + 1, z - 1, z + 1)
        assert bottom > 0, "insert bore breaks through the flange"
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
