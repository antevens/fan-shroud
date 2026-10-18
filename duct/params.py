"""Every dimension of the duct, loaded from a TOML config."""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path


class ConfigError(ValueError):
    """Raised when the TOML config contains unknown keys or invalid values."""


@dataclass
class Params:
    """All dimensions in millimetres. Field names match the TOML keys.

    Duct frame:
      X along the cards, 0 at the bracket plane, negative toward the case front.
      Y away from the motherboard surface, 0 at the motherboard.
      Z vertical, 0 at the floor of the bottom-most covered channel.
    """

    # --- printer ---
    printer_model: str = "Elegoo Centauri Carbon 2 Combo"
    bed_x: float = 256.0
    bed_y: float = 256.0
    bed_z: float = 256.0
    nozzle_diameter: float = 0.4
    bed_margin: float = 5.0

    # --- fan (80 mm primary) ---
    fan_size: float = 80.0
    fan_depth: float = 25.0
    fan_hole_spacing: float = 71.5
    fan_hole_diameter: float = 4.3
    fan_flange_size: float = 83.0
    fan_flange_thickness: float = 6.0
    fan_screw_clearance: float = 5.2
    fan_screw_head_clearance: float = 7.6
    fan_screw_seat: float = 3.0
    fan_screw_tube_wall: float = 1.6
    fan_screw_length: float = 10.0
    fan_corner_pad: float = 9.0
    fan_gusset_tip: float = 2.0
    fan_gpu_clearance: float = 3.0
    fan_intake_clearance: float = 20.0
    fan_center_y: float | None = None
    fan_center_z: float | None = None
    # Card-clip: the fan bolts straight onto the shroud's tail end wall.
    tail_fan_size: float = 60.0
    tail_fan_depth: float = 25.0
    tail_fan_hole_spacing: float = 50.0
    tail_fan_opening: float = 57.0
    tail_fan_center_y: float | None = None
    tail_fan_center_z: float | None = None
    tail_clearance: float = 4.0
    tail_wall_thickness: float = 3.0
    free_length_past_cards: float = 35.0
    # Card-clip: tab laid on the PCI bracket tabs, held by the bracket screws (axis along Y).
    bracket_tab_y: float = 110.0
    bracket_screw_x: float = -6.0
    bracket_screw_dz: float = 0.0
    bracket_tab_thickness: float = 2.0
    bracket_tab_depth: float = 12.0
    bracket_screw_clearance: float = 4.0
    bracket_arm_width: float = 10.0

    # --- slots and GPU ---
    slot_pitch: float = 20.32
    slot_positions_covered: int = 3
    channel_floor_below_pcb: float = 16.0
    bottom_slot_pcb_to_midplate: float = 40.0
    gpu_slot_gap: int = 3
    gpu_underside_below_pcb: float = 52.0
    gpu_length: float = 344.0
    gpu_top_clearance: float = 1.5

    # --- cards and case ---
    outlet_card_clearance: float = 5.0
    exhaust_gap: float = 20.0
    card_top_margin: float = 2.0
    connector_height: float = 11.25
    motherboard_clearance: float = 5.0
    side_clearance: float = 110.0
    free_length_from_outlet: float = 80.0
    under_midplate_gap: float = 15.0
    cutouts: list[list[float]] = field(default_factory=list)

    # --- midplate perforations ---
    hole_pattern: str = "slots"
    hole_diameter: float = 3.0
    hole_pitch: float = 9.5
    hole_row_pitch_override: float | None = 5.5
    slot_length: float = 7.0
    slot_width: float = 3.0
    sheet_thickness: float = 0.8
    perforation_origin_x: float = 0.0
    perforation_origin_y: float = 0.0

    # --- duct body ---
    wall_thickness: float = 2.0
    min_wall_thickness: float = 1.6
    vane_thickness: float = 1.6
    transition_length: float | None = None
    max_expansion_half_angle: float = 15.0
    max_contraction_half_angle: float = 40.0
    gasket_lip_width: float = 2.5
    gasket_lip_thickness: float = 2.0
    gasket_lip_sides: list[str] = field(default_factory=lambda: ["y_min", "z_min"])
    outlet_gasket_thickness: float = 2.5
    flange_chamfer: float = 1.0
    zip_tie_slot_width: float = 4.0
    zip_tie_slot_height: float = 2.0
    zip_tie_pair_spacing: float = 10.0

    # --- blanking plugs ---
    plug_clearance: float = 0.3
    plug_depth: float = 10.0
    plug_plate_thickness: float = 2.0
    plug_handle_height: float = 8.0
    plug_handle_length: float = 30.0
    plug_handle_thickness: float = 2.0

    # --- floor tray and pins ---
    tray_thickness: float = 1.6
    tray_y_min: float = 2.0
    tray_lip_height: float = 2.0
    tray_lip_width: float = 2.0
    tray_edge_margin: float = 6.0
    peg_clearance: float = 0.2
    pin_head_diameter: float = 6.0
    pin_head_thickness: float = 1.6
    pin_protrusion: float = 1.0
    pin_hole_clearance: float = 0.1
    pin_count_x: int = 3
    pin_count_y: int = 2

    # --- side cover (case mount) and card-clip shroud ---
    side_cover: bool = True
    cover_edge_chamfer: float = 1.5
    pcb_thickness: float = 1.57
    pcb_seat_offset: float = 3.5
    reference_pcb_height: float = 68.9
    card_lengths: list[float] = field(default_factory=lambda: [152.0, 142.24, 167.64])
    card_pcb_heights: list[float] = field(default_factory=lambda: [68.9, 68.9, 68.9])
    grip_fill: str = "grip"
    grip_engagement: float = 2.5
    grip_wall: float = 1.5
    grip_back_min: float = 5.5
    grip_screw_diameter: float = 2.5
    grip_screw_pilot: float = 1.8
    tpu_min_wall_thickness: float = 1.2
    grip_screw_x: list[float] = field(default_factory=lambda: [-55.0, -100.0, -145.0])
    grip_interference: float = 0.2
    grip_margin: float = 4.0
    pocket_clearance: float = 0.2
    pocket_rib: float = 1.6
    pocket_reach: float = 2.5
    roof_clearance: float = 0.3
    stub_overlap: float = 2.0
    grip_material: str = "TPU 72D"
    grip_lip_material: str = "TPU 95A"

    # --- mount ---
    mount_style: str = "case"
    joint_gasket_thickness: float = 1.0
    mount_bar_depth: float = 9.0
    mount_groove_clearance: float = 0.3
    groove_fence_height: float = 7.0
    fan_foot: bool = False
    foot_depth: float = 16.0
    foot_overlap: float = 1.0
    foot_pin_count: int = 2

    # --- booster ---
    booster: str = "none"
    booster_fan_size: float = 120.0
    booster_fan_depth: float = 15.0
    booster_hole_spacing: float = 105.0
    booster_hole_diameter: float = 4.3
    booster_intake_clearance: float = 15.0

    # --- print ---
    material: str = "ABS"
    gasket_material: str = "TPU 95A"

    # --- bookkeeping ---
    place_example_plug: bool = False
    unmeasured: list[str] = field(default_factory=list)

    # ----- midplate, slots, GPU -----

    @property
    def midplate_gap(self) -> float:
        return self.bottom_slot_pcb_to_midplate - self.channel_floor_below_pcb

    @property
    def midplate_z(self) -> float:
        return -self.midplate_gap

    @property
    def top_covered_pcb_z(self) -> float:
        return (self.slot_positions_covered - 1) * self.slot_pitch + self.channel_floor_below_pcb

    @property
    def gpu_pcb_z(self) -> float:
        return self.top_covered_pcb_z + self.gpu_slot_gap * self.slot_pitch

    @property
    def gpu_plane_z(self) -> float:
        """Underside of the GPU's shroud above the top covered channel."""
        return self.gpu_pcb_z - self.gpu_underside_below_pcb

    @property
    def gpu_clearance(self) -> float:
        """Gap between the top of the top covered channel grid line and the GPU underside."""
        return self.gpu_plane_z - self.slot_positions_covered * self.slot_pitch

    # ----- cards -----

    @property
    def longest_card_length(self) -> float:
        return max(self.card_lengths)

    @property
    def shortest_card_length(self) -> float:
        return min(self.card_lengths)

    def card_top_edge(self, slot: int) -> float:
        """Y of the seated card's top PCB edge in covered slot `slot` (0 = bottom)."""
        return self.pcb_seat_offset + self.card_pcb_heights[slot]

    @property
    def card_top_height(self) -> float:
        return max(self.card_top_edge(k) for k in range(len(self.card_pcb_heights)))

    @property
    def reference_top_edge(self) -> float:
        """Top edge of a seated card at the low-profile reference height; sets the wall position."""
        return self.pcb_seat_offset + self.reference_pcb_height

    @property
    def grip_slot_width(self) -> float:
        return self.pcb_thickness - self.grip_interference

    @property
    def grip_outer_width(self) -> float:
        """Grip size along Z (across the PCB)."""
        return self.grip_slot_width + 2 * self.grip_wall

    def grip_back(self, slot: int) -> float:
        """Back thickness of the grip for `slot`.

        grip_fill = "grip": the back grows so every grip reaches the wall (shroud stays card-agnostic).
        grip_fill = "wall": every grip has the same thin back and a pad in the pocket fills the gap.
        """
        if self.grip_fill == "grip":
            return self.shroud_wall_inner_y - self.card_top_edge(slot)
        return self.grip_back_min

    def grip_height(self, slot: int) -> float:
        """Grip size along Y: engagement on the PCB plus its back."""
        return self.grip_engagement + self.grip_back(slot)

    def grip_back_y(self, slot: int) -> float:
        return self.card_top_edge(slot) + self.grip_back(slot)

    def grip_length(self, slot: int) -> float:
        return self.card_lengths[slot] - self.exhaust_gap - 2 * self.grip_margin

    def grip_x_range(self, slot: int) -> tuple[float, float]:
        x0 = -self.card_lengths[slot] + self.grip_margin
        return x0, x0 + self.grip_length(slot)

    def grip_lip_change_z(self, slot: int) -> float:
        """Print height at which the grip changes from the back material to the lip material."""
        return self.grip_back(slot)

    def grip_screw_positions(self, slot: int) -> list[float]:
        """Wall screw positions that the grip of `slot` actually reaches."""
        x0, x1 = self.grip_x_range(slot)
        margin = self.grip_screw_diameter
        return [x for x in self.grip_screw_x if x0 + margin <= x <= x1 - margin]

    def grip_screw_local_x(self, slot: int) -> list[float]:
        """Screw positions along the grip in its own frame (0 at the grip's centre)."""
        x0, x1 = self.grip_x_range(slot)
        centre = (x0 + x1) / 2
        return [x - centre for x in self.grip_screw_positions(slot)]

    # ----- outlet -----

    @property
    def outlet_offset_from_bracket(self) -> float:
        return self.longest_card_length + self.outlet_card_clearance

    @property
    def outlet_x(self) -> float:
        return -self.outlet_offset_from_bracket

    @property
    def outlet_y_min(self) -> float:
        return self.motherboard_clearance + self.gasket_lip_width + self.wall_thickness

    @property
    def outlet_y_max(self) -> float:
        """Inner face of the side wall: the tallest card's grip back touches it (card-clip) or a margin (case)."""
        if self.mount_style == "card_clip":
            return self.reference_top_edge + self.grip_back_min
        return self.card_top_height + self.card_top_margin

    @property
    def card_zone_height(self) -> float:
        return self.outlet_y_max - self.outlet_y_min

    @property
    def outlet_z_min(self) -> float:
        return 0.0

    @property
    def outlet_z_max_grid(self) -> float:
        return self.slot_positions_covered * self.slot_pitch

    def lip(self, side: str) -> float:
        """Gasket lip width on one outlet side; sides without a lip are butted by the shroud or cover."""
        return self.gasket_lip_width if side in self.gasket_lip_sides else 0.0

    @property
    def top_wall_total(self) -> float:
        return self.wall_thickness + self.lip("z_max")

    @property
    def outlet_z_max(self) -> float:
        """Top of the outlet opening.

        Card-clip: the top card's PCB back is the roof, so the opening stops just above it.
        Case: the grid line, trimmed below it when the GPU sits too close.
        """
        if self.mount_style == "card_clip":
            top = self.slot_positions_covered - 1
            return self.pcb_z(top) + self.pcb_thickness / 2 + self.roof_clearance
        limit = self.gpu_plane_z - self.gpu_top_clearance - self.top_wall_total
        return min(self.outlet_z_max_grid, limit)

    @property
    def top_channel_trim(self) -> float:
        return self.outlet_z_max_grid - self.outlet_z_max

    @property
    def channel_boundaries_z(self) -> list[float]:
        n = self.slot_positions_covered
        bounds = [self.outlet_z_min + k * self.slot_pitch for k in range(n)]
        return bounds + [self.outlet_z_max]

    # ----- fan end -----

    @property
    def fan_inner(self) -> float:
        return self.fan_size - 2 * self.wall_thickness

    @property
    def fan_inner_x(self) -> float:
        """X of the fan-side end of the transition (inner face of the flange)."""
        return self.outlet_x - self.transition_length_eff

    @property
    def fan_face_x(self) -> float:
        """X of the flange face the fan bolts to."""
        return self.fan_inner_x - self.fan_flange_thickness

    @property
    def fan_intake_x(self) -> float:
        return self.fan_face_x - self.fan_depth

    @property
    def fan_end_size(self) -> float:
        return max(self.fan_size, self.fan_flange_size)

    @property
    def fan_center_z_eff(self) -> float:
        """Fan axis height: as high as the GPU allows unless overridden."""
        if self.fan_center_z is not None:
            return self.fan_center_z
        return self.gpu_plane_z - self.fan_gpu_clearance - self.fan_end_size / 2

    @property
    def fan_center_y_eff(self) -> float:
        if self.fan_center_y is not None:
            return self.fan_center_y
        centred = (self.outlet_y_min + self.outlet_y_max) / 2
        lowest = self.motherboard_clearance + self.fan_end_size / 2
        return max(centred, lowest)

    @property
    def fan_inner_y_min(self) -> float:
        return self.fan_center_y_eff - self.fan_inner / 2

    @property
    def fan_inner_y_max(self) -> float:
        return self.fan_center_y_eff + self.fan_inner / 2

    @property
    def fan_inner_z_min(self) -> float:
        return self.fan_center_z_eff - self.fan_inner / 2

    @property
    def fan_inner_z_max(self) -> float:
        return self.fan_center_z_eff + self.fan_inner / 2

    @property
    def flange_bottom_z(self) -> float:
        return self.fan_center_z_eff - self.fan_flange_size / 2

    @property
    def fan_end_bottom_z(self) -> float:
        return self.fan_center_z_eff - self.fan_end_size / 2

    @property
    def fan_end_top_z(self) -> float:
        return self.fan_center_z_eff + self.fan_end_size / 2

    # ----- transition geometry -----

    def side_deltas(self) -> dict[str, float]:
        """Outward growth of each wall from the fan end to the outlet end (negative = contraction)."""
        return {
            "y_min": self.fan_inner_y_min - self.outlet_y_min,
            "y_max": self.outlet_y_max - self.fan_inner_y_max,
            "z_min": self.fan_inner_z_min - self.outlet_z_min,
            "z_max": self.outlet_z_max - self.fan_inner_z_max,
        }

    def min_transition_length(self) -> float:
        """Shortest transition keeping expansions and contractions within their angle limits."""
        needed = 0.0
        for delta in self.side_deltas().values():
            limit = self.max_expansion_half_angle if delta > 0 else self.max_contraction_half_angle
            needed = max(needed, abs(delta) / math.tan(math.radians(limit)))
        return float(math.ceil(needed))

    @property
    def transition_length_eff(self) -> float:
        if self.transition_length is not None:
            return self.transition_length
        return self.min_transition_length()

    def side_tilt_angles(self) -> dict[str, float]:
        """Tilt of each transition wall from the X axis, in degrees (negative = contraction)."""
        length = self.transition_length_eff
        return {k: math.degrees(math.atan(d / length)) for k, d in self.side_deltas().items()}

    def max_half_angle(self) -> float:
        return max(abs(a) for a in self.side_tilt_angles().values())

    def angle_violations(self) -> list[str]:
        out = []
        for side, angle in self.side_tilt_angles().items():
            limit = self.max_expansion_half_angle if angle > 0 else self.max_contraction_half_angle
            if abs(angle) > limit + 1e-6:
                out.append(f"{side} wall tilts {angle:.1f} deg, limit {limit:g}")
        return out

    def wall_normal_offset(self, side: str) -> float:
        """Outward wall offset so the perpendicular thickness equals wall_thickness."""
        tilt = math.radians(self.side_tilt_angles()[side])
        return self.wall_thickness / math.cos(tilt)

    def body_bottom_outer_z(self, x: float) -> float:
        """Z of the body's outer bottom surface at X (between the flange and the outlet)."""
        frac = (x - self.fan_inner_x) / self.transition_length_eff
        inner = self.fan_inner_z_min + frac * (self.outlet_z_min - self.fan_inner_z_min)
        return inner - self.wall_normal_offset("z_min")

    # ----- outlet frame -----

    def frame_bounds(self) -> tuple[float, float, float, float]:
        """Outer (y0, y1, z0, z1) of the outlet gasket frame."""
        return (
            self.outlet_y_min - self.wall_normal_offset("y_min") - self.lip("y_min"),
            self.outlet_y_max + self.wall_normal_offset("y_max") + self.lip("y_max"),
            self.outlet_z_min - self.wall_normal_offset("z_min") - self.lip("z_min"),
            self.outlet_z_max + self.wall_normal_offset("z_max") + self.lip("z_max"),
        )

    @property
    def duct_top_z(self) -> float:
        return max(self.frame_bounds()[3], self.fan_end_top_z)

    @property
    def duct_bottom_z(self) -> float:
        """Outer bottom of the duct body at the outlet plane."""
        return self.outlet_z_min - self.wall_normal_offset("z_min")

    # ----- side cover -----

    @property
    def cover_x_min(self) -> float:
        return self.outlet_x + self.outlet_gasket_thickness

    @property
    def cover_x_max(self) -> float:
        """Cover stops just short of the tray's exhaust-end rim."""
        return self.tray_x_max - self.tray_lip_width - self.mount_groove_clearance

    @property
    def cover_y_min(self) -> float:
        """Lid edge nearest the motherboard, clear of the slot connector housings."""
        return self.connector_height + 1.0

    @property
    def cover_y_outer(self) -> float:
        return self.frame_bounds()[1]

    @property
    def cover_y_inner(self) -> float:
        return self.cover_y_outer - self.wall_thickness

    @property
    def cover_lid_bottom_z(self) -> float:
        return self.outlet_z_max

    @property
    def cover_lid_top_z(self) -> float:
        return self.cover_lid_bottom_z + self.wall_thickness

    # ----- mount joint (duct mount bar into tray groove) -----

    @property
    def has_mount_bar(self) -> bool:
        return self.mount_style == "case"

    @property
    def mount_bar_bottom_z(self) -> float:
        return self.frame_bounds()[2] - self.mount_bar_depth

    @property
    def groove_floor_z(self) -> float:
        return self.mount_bar_bottom_z - self.joint_gasket_thickness

    @property
    def fence_top_z(self) -> float:
        return self.groove_floor_z + self.groove_fence_height

    @property
    def groove_x_min(self) -> float:
        return self.outlet_x - self.gasket_lip_thickness - self.mount_groove_clearance

    @property
    def groove_x_max(self) -> float:
        return self.outlet_x + self.mount_groove_clearance

    @property
    def upstand_x_min(self) -> float:
        return self.groove_x_min - self.wall_thickness

    @property
    def upstand_x_max(self) -> float:
        return self.groove_x_max + self.wall_thickness

    @property
    def tray_top_z(self) -> float:
        return self.midplate_z + self.tray_thickness

    @property
    def upstand_height(self) -> float:
        return self.groove_floor_z - self.tray_top_z

    @property
    def zip_tie_z(self) -> float:
        return (self.mount_bar_bottom_z + self.fence_top_z) / 2

    # ----- tray -----

    @property
    def tray_x_min(self) -> float:
        return self.upstand_x_min

    @property
    def tray_x_max(self) -> float:
        return -self.exhaust_gap

    @property
    def tray_y_max(self) -> float:
        return self.cover_y_outer + self.mount_groove_clearance + self.tray_lip_width

    # ----- card-clip shroud -----

    @property
    def shroud_x_min(self) -> float:
        if self.mount_style == "card_clip":
            # Tail end wall just past the longest card; the fan bolts onto its outer face.
            return -(self.longest_card_length + self.tail_clearance + self.tail_wall_thickness)
        return self.outlet_x + self.outlet_gasket_thickness

    # ----- card-clip tail fan and bracket tab -----

    @property
    def tail_wall_y_range(self) -> tuple[float, float]:
        return self.motherboard_clearance, self.shroud_wall_outer_y

    @property
    def tail_wall_z_range(self) -> tuple[float, float]:
        return self.shroud_bottom_z, self.outlet_z_max + self.wall_thickness

    @property
    def tail_fan_center_y_eff(self) -> float:
        if self.tail_fan_center_y is not None:
            return self.tail_fan_center_y
        centred = (self.pcb_seat_offset + self.reference_top_edge) / 2
        return max(centred, self.motherboard_clearance + self.tail_fan_size / 2)

    @property
    def tail_fan_center_z_eff(self) -> float:
        if self.tail_fan_center_z is not None:
            return self.tail_fan_center_z
        return (self.outlet_z_min + self.outlet_z_max) / 2

    @property
    def tail_fan_intake_x(self) -> float:
        return self.shroud_x_min - self.tail_fan_depth

    def tail_fan_hole_points(self) -> list[tuple[float, float]]:
        half = self.tail_fan_hole_spacing / 2
        cy, cz = self.tail_fan_center_y_eff, self.tail_fan_center_z_eff
        return [(cy + sy * half, cz + sz * half) for sy in (-1, 1) for sz in (-1, 1)]

    def bracket_screw_points(self) -> list[float]:
        """Z of each covered slot's bracket screw."""
        return [self.pcb_z(k) + self.bracket_screw_dz for k in range(self.slot_positions_covered)]

    def bracket_arm_outline(self) -> list[tuple[float, float]]:
        """XY outline of a bracket rib: along the wall's outer face to the shroud's bracket-end edge, then
        angled up to the ear on the bracket tab.

        The lower edge follows the wall face to the edge and then climbs straight to the ear's inner bottom
        corner, so nothing sits under the ear where the metal bracket tab and the slot rail are. The upper
        edge runs at 45 deg from the rib's root on the wall to the ear's outer face, which keeps the rib
        printable standing on the tail wall and makes it deepest where it leaves the shroud.
        """
        tab_x0, tab_x1 = self.bracket_tab_x_range
        y_out = self.shroud_wall_outer_y
        y_tab = self.bracket_tab_y
        y_top = y_tab + self.bracket_tab_thickness
        x_edge = self.shroud_x_max
        x_root = min(x_edge - 2.0, tab_x0 - (y_top - y_out))
        fuse = y_out - 0.5                      # root sunk into the wall so the rib fuses to it
        return [(x_root, fuse), (x_edge, fuse), (x_edge, y_out), (tab_x0, y_tab), (tab_x1, y_tab),
                (tab_x1, y_top), (tab_x0, y_top), (x_root, y_out)]

    @property
    def bracket_tab_x_range(self) -> tuple[float, float]:
        half = self.bracket_tab_depth / 2
        return self.bracket_screw_x - half, self.bracket_screw_x + half

    @property
    def shroud_x_max(self) -> float:
        return -self.exhaust_gap

    @property
    def shroud_wall_inner_y(self) -> float:
        return self.outlet_y_max

    @property
    def shroud_wall_outer_y(self) -> float:
        """Flush with the flange so the wall lies flat on the bed when printed wall-down."""
        return self.frame_bounds()[1]

    @property
    def shroud_bottom_z(self) -> float:
        return self.outlet_z_min - self.wall_thickness

    def pcb_z(self, slot: int) -> float:
        """PCB plane of covered slot index `slot` (0 = bottom)."""
        return slot * self.slot_pitch + self.channel_floor_below_pcb

    def pocket_z_range(self, slot: int) -> tuple[float, float]:
        """Z span of the wall pocket that receives the grip of `slot`."""
        half = self.grip_outer_width / 2 + self.pocket_clearance
        return self.pcb_z(slot) - half, self.pcb_z(slot) + half

    def pocket_rib_z_ranges(self, slot: int) -> list[tuple[float, float]]:
        z0, z1 = self.pocket_z_range(slot)
        return [(z0 - self.pocket_rib, z0), (z1, z1 + self.pocket_rib)]

    def pocket_floor_y(self, slot: int) -> float:
        """Y where the grip back of `slot` meets the wall (a pad fills up to the wall for shorter cards)."""
        return self.grip_back_y(slot)

    def pocket_inner_y(self, slot: int) -> float:
        """How far the pocket ribs of `slot` reach inward from the wall face.

        grip_fill = "grip": a fixed pocket_reach from the wall for every slot, so the shroud does not
        depend on the card heights. grip_fill = "wall": past that card's edge by pocket_reach.
        """
        if self.grip_fill == "grip":
            return self.shroud_wall_inner_y - self.pocket_reach
        return self.card_top_edge(slot) - self.pocket_reach

    @property
    def pocket_inner_y_min(self) -> float:
        return min(self.pocket_inner_y(k) for k in range(self.slot_positions_covered))

    @property
    def shroud_top_z(self) -> float:
        top = self.slot_positions_covered - 1
        rib_top = self.pocket_rib_z_ranges(top)[1][1]
        return max(rib_top, self.outlet_z_max + self.wall_thickness)

    @property
    def stub_x_max(self) -> float:
        """Lid stub covers from the flange to the top card's tail plus an overlap."""
        return -self.card_lengths[self.slot_positions_covered - 1] + self.stub_overlap

    # ----- pins and perforations -----

    @property
    def pin_diameter(self) -> float:
        return self.hole_diameter - self.peg_clearance

    @property
    def pin_shaft_length(self) -> float:
        return self.tray_thickness + self.sheet_thickness + self.pin_protrusion

    @property
    def pin_hole_diameter(self) -> float:
        return self.pin_diameter + self.pin_hole_clearance

    @property
    def peg_x(self) -> float:
        """Peg size along X for slot perforations."""
        return self.slot_length - self.peg_clearance

    @property
    def peg_y(self) -> float:
        return self.slot_width - self.peg_clearance

    @property
    def hole_row_pitch(self) -> float:
        if self.hole_row_pitch_override is not None:
            return self.hole_row_pitch_override
        if self.hole_pattern == "hex":
            return self.hole_pitch * math.sqrt(3) / 2
        return self.hole_pitch

    @property
    def staggered(self) -> bool:
        return self.hole_pattern in ("hex", "slots")

    # ----- foot under the fan -----

    @property
    def foot_x_min(self) -> float:
        return self.fan_face_x - self.foot_depth

    @property
    def foot_x_max(self) -> float:
        return self.fan_inner_x

    @property
    def foot_top_z(self) -> float:
        return self.flange_bottom_z + self.foot_overlap

    @property
    def foot_rim_top_z(self) -> float:
        return self.flange_bottom_z + self.flange_chamfer

    @property
    def foot_height(self) -> float:
        return self.foot_top_z - self.midplate_z

    @property
    def foot_flat_x_max(self) -> float:
        return self.foot_x_max - (self.foot_rim_top_z - self.midplate_z)

    # ----- cutouts -----

    def overlaps_cutout(self, x0: float, x1: float, y0: float, y1: float) -> list[list[float]]:
        """Cutouts intersecting the given footprint."""
        hits = []
        for cx0, cx1, cy0, cy1 in self.cutouts:
            if x0 < cx1 and x1 > cx0 and y0 < cy1 and y1 > cy0:
                hits.append([cx0, cx1, cy0, cy1])
        return hits

    # ----- validation -----

    def duct_violations(self) -> list[str]:
        """Checks for the separate 80 mm duct, built only with the case mount."""
        problems: list[str] = []
        problems += self.angle_violations()
        if self.fan_end_top_z > self.gpu_plane_z - self.fan_gpu_clearance + 1e-6:
            problems.append("fan end collides with the GPU underside; set fan_center_z lower")
        if self.fan_end_bottom_z < self.midplate_z:
            problems.append(
                f"fan end bottom {self.fan_end_bottom_z:.1f} is below the midplate {self.midplate_z:.1f}; "
                "the slot stack plus midplate gap is too short for this fan"
            )
        if self.fan_center_y_eff - self.fan_end_size / 2 < self.motherboard_clearance - 1e-6:
            problems.append("fan end is closer to the motherboard than motherboard_clearance")
        if self.flange_chamfer > min(self.fan_flange_thickness, (self.fan_flange_size - self.fan_size) / 2):
            problems.append("flange_chamfer exceeds the flange overhang or thickness")
        half = self.fan_hole_spacing / 2
        if self.fan_flange_size / 2 - (half + self.fan_screw_head_clearance / 2) < self.min_wall_thickness:
            problems.append("fan screw head bore too close to the flange edge; enlarge fan_flange_size")
        if (half - self.fan_screw_clearance / 2) - (self.fan_inner / 2 - self.fan_corner_pad) < self.min_wall_thickness:
            problems.append("fan screw hole too close to the corner pad's inner edge; enlarge fan_corner_pad")
        if not self.min_wall_thickness <= self.fan_screw_seat < self.fan_flange_thickness:
            problems.append("fan_screw_seat must be at least min_wall_thickness and thinner than the flange")
        if self.fan_screw_length - self.fan_screw_seat < 4.0:
            problems.append("fan screws reach under 4 mm into the fan frame; use longer screws or a thinner fan_screw_seat")
        if self.fan_screw_tube_wall < self.min_wall_thickness:
            problems.append("fan_screw_tube_wall must be at least min_wall_thickness")
        if half + self.fan_screw_head_clearance / 2 + self.fan_screw_tube_wall > self.fan_flange_size / 2 + 1e-6:
            problems.append("fan screw tubes reach past the flange outline; enlarge fan_flange_size")
        if self.fan_gusset_tip < self.min_wall_thickness:
            problems.append("fan_gusset_tip must be at least min_wall_thickness")
        if self.fan_foot:
            if self.foot_overlap >= self.flange_chamfer:
                problems.append("foot_overlap must be below flange_chamfer so the foot clears the fan frame")
            if self.foot_flat_x_max - self.foot_x_min < 2 * self.tray_edge_margin:
                problems.append("foot_depth too short for a pin on the flat part of the foot")
            fy0 = self.fan_center_y_eff - self.fan_flange_size / 2
            fy1 = self.fan_center_y_eff + self.fan_flange_size / 2
            if self.overlaps_cutout(self.foot_x_min, self.foot_x_max, fy0, fy1):
                problems.append("fan foot lands on a midplate cutout; set fan_foot = false")
        needed = -self.fan_intake_x + self.fan_intake_clearance
        available = self.outlet_offset_from_bracket + self.free_length_from_outlet
        if needed > available:
            problems.append(
                f"duct plus fan needs {needed:.0f} mm from the bracket but only {available:.0f} mm is free"
            )
        return problems

    def tail_violations(self) -> list[str]:
        """Checks for the card-clip shroud's tail fan and bracket tab."""
        problems: list[str] = []
        cy, cz, half = self.tail_fan_center_y_eff, self.tail_fan_center_z_eff, self.tail_fan_size / 2
        wy0, wy1 = self.tail_wall_y_range
        if cy - half < wy0 - 1e-6 or cy + half > wy1 + 1e-6:
            problems.append("tail fan overhangs the end wall across the card zone; move tail_fan_center_y")
        if cz + half > self.gpu_plane_z - self.fan_gpu_clearance + 1e-6:
            problems.append("tail fan collides with the GPU underside; move tail_fan_center_z lower")
        if cz - half < self.midplate_z - 1e-6:
            problems.append("tail fan reaches below the midplate")
        hole_r = self.tail_fan_hole_spacing / 2 * math.sqrt(2)
        if self.tail_fan_opening / 2 + self.min_wall_thickness > hole_r - self.fan_screw_clearance / 2:
            problems.append("tail_fan_opening cuts into the fan screw holes")
        if self.tail_wall_thickness < self.min_wall_thickness:
            problems.append("tail_wall_thickness is below min_wall_thickness")
        if self.fan_screw_length - self.tail_wall_thickness < 4.0:
            problems.append("fan screws reach under 4 mm into the fan frame through the tail wall")
        needed = -self.tail_fan_intake_x
        available = self.longest_card_length + self.free_length_past_cards
        if needed > available + 1e-6:
            problems.append(f"shroud plus fan needs {needed:.0f} mm from the bracket but only {available:.0f} mm is free")
        _, x1 = self.bracket_tab_x_range
        if x1 > 1e-6:
            problems.append("bracket tab reaches past the bracket plane")
        if self.bracket_tab_y < self.shroud_wall_outer_y + 1e-6:
            problems.append("bracket_tab_y must lie beyond the shroud wall's outer face")
        if self.bracket_tab_thickness < self.min_wall_thickness:
            problems.append("bracket_tab_thickness is below min_wall_thickness")
        if self.bracket_tab_depth - self.bracket_screw_clearance < 2 * self.min_wall_thickness:
            problems.append("bracket ear too short around the screw hole; raise bracket_tab_depth")
        if self.bracket_arm_width - self.bracket_screw_clearance < 2 * self.min_wall_thickness:
            problems.append("bracket ear too narrow around the screw hole; raise bracket_arm_width")
        if self.bracket_arm_width > self.slot_pitch - 2.0:
            problems.append("bracket arms of neighbouring slots touch; reduce bracket_arm_width")
        outline = self.bracket_arm_outline()
        fin_start = outline[0][0]
        if self.bracket_tab_x_range[0] < self.shroud_x_max + self.min_wall_thickness:
            problems.append("bracket ears must start beyond the shroud's bracket-end edge; move bracket_screw_x toward 0")
        if max(self.grip_screw_x) + self.grip_screw_diameter > fin_start:
            problems.append(f"grip screws at x > {fin_start - self.grip_screw_diameter:.0f} sit behind the bracket ribs; "
                            "move grip_screw_x toward the card tails")
        zs = self.bracket_screw_points()
        if max(zs) + self.bracket_arm_width / 2 > self.gpu_plane_z - self.gpu_top_clearance + 1e-6:
            problems.append("top bracket arm reaches the GPU underside")
        if min(zs) - self.bracket_arm_width / 2 < self.midplate_z + 1e-6:
            problems.append("bottom bracket arm reaches the midplate")
        return problems

    def validate(self) -> list[str]:
        problems: list[str] = []
        if self.slot_positions_covered < 1:
            problems.append("slot_positions_covered must be at least 1")
        bad_sides = sorted(set(self.gasket_lip_sides) - {"y_min", "y_max", "z_min", "z_max"})
        if bad_sides:
            problems.append(f"gasket_lip_sides contains unknown sides: {', '.join(bad_sides)}")
        if self.hole_pattern not in ("square", "hex", "slots"):
            problems.append(f"hole_pattern must be 'square', 'hex' or 'slots', got {self.hole_pattern!r}")
        if self.mount_style not in ("case", "card_clip"):
            problems.append(f"mount_style must be 'case' or 'card_clip', got {self.mount_style!r}")
        if self.booster not in ("none", "side_cover_120"):
            problems.append(f"booster must be 'none' or 'side_cover_120', got {self.booster!r}")
        for name in ("wall_thickness", "vane_thickness", "outlet_gasket_thickness", "plug_handle_thickness"):
            if getattr(self, name) < self.min_wall_thickness:
                problems.append(f"{name} is below min_wall_thickness")
        if self.midplate_gap <= 0:
            problems.append("bottom_slot_pcb_to_midplate must exceed channel_floor_below_pcb")
            return problems
        for cut in self.cutouts:
            if len(cut) != 4:
                problems.append("each cutout needs [x0, x1, y0, y1]")
                return problems
        if self.outlet_z_max <= (self.slot_positions_covered - 1) * self.slot_pitch + 5:
            problems.append("GPU sits so low that the top covered channel has under 5 mm left; reduce slot_positions_covered")
            return problems
        if self.mount_style == "case":
            problems += self.duct_violations()
        else:
            problems += self.tail_violations()
        if self.mount_style == "case":
            if self.upstand_height < 0:
                problems.append(
                    f"groove floor {self.groove_floor_z:.1f} is below the tray top {self.tray_top_z:.1f}; "
                    "reduce mount_bar_depth or tray_thickness"
                )
            limit = self.body_bottom_outer_z(self.upstand_x_min) - 0.5
            if self.fence_top_z > limit:
                problems.append(
                    f"groove fence top {self.fence_top_z:.1f} hits the duct underside {limit:.1f}; "
                    "reduce groove_fence_height or increase mount_bar_depth"
                )
        if self.side_cover and self.cover_lid_top_z > self.gpu_plane_z - self.gpu_top_clearance + 1e-6:
            problems.append("side cover lid collides with the GPU underside")
        if self.cover_edge_chamfer > self.wall_thickness - 0.4:
            problems.append("cover_edge_chamfer must be at least 0.4 mm less than wall_thickness")
        n = self.slot_positions_covered
        if len(self.card_lengths) != n or len(self.card_pcb_heights) != n:
            problems.append("card_lengths and card_pcb_heights need one entry per covered slot, bottom first")
            return problems
        if self.mount_style == "card_clip":
            for slot, height in enumerate(self.card_pcb_heights):
                if height > self.reference_pcb_height + 1e-6:
                    problems.append(f"card in slot {slot + 1} is taller than reference_pcb_height; raise the reference")
        if self.grip_fill not in ("grip", "wall"):
            problems.append(f"grip_fill must be 'grip' or 'wall', got {self.grip_fill!r}")
        if self.mount_style == "card_clip":
            if self.shroud_top_z > self.gpu_plane_z - self.gpu_top_clearance + 1e-6:
                problems.append("shroud wall top collides with the GPU underside")
            if self.pocket_rib < self.min_wall_thickness:
                problems.append("pocket_rib must be at least min_wall_thickness")
            if self.grip_wall < self.tpu_min_wall_thickness:
                problems.append("grip_wall must be at least tpu_min_wall_thickness")
            if self.grip_back_min - self.tpu_min_wall_thickness < 3.0:
                problems.append("grip_back_min must leave tpu_min_wall_thickness under a 3 mm deep screw pilot")
            if (self.grip_outer_width - self.grip_screw_pilot) / 2 < self.tpu_min_wall_thickness:
                problems.append("grip walls beside the screw pilot are thinner than tpu_min_wall_thickness; raise grip_wall")
            for slot in range(n):
                if len(self.grip_screw_positions(slot)) < 2:
                    problems.append(f"grip for slot {slot + 1} reaches fewer than two screw positions")
            if self.grip_engagement < 1.5:
                problems.append("grip_engagement under 1.5 mm will not seal")
            if self.grip_fill == "wall" and self.pocket_reach > self.grip_engagement:
                problems.append("pocket_reach must not exceed grip_engagement")
            for slot in range(n):
                if self.grip_length(slot) < 20:
                    problems.append(f"grip for slot {slot + 1} would be under 20 mm long")
                if slot < n - 1:
                    gap = self.pocket_rib_z_ranges(slot + 1)[0][0] - self.pocket_rib_z_ranges(slot)[1][1]
                    if gap < 0:
                        problems.append("pockets of neighbouring slots overlap; reduce grip_wall or pocket_rib")
            if self.stub_x_max < self.shroud_x_min + self.tail_wall_thickness:
                problems.append("top card is shorter than the shroud start; lid stub cannot reach it")
        return problems


def _flatten(data: dict) -> dict:
    flat: dict = {}
    for key, value in data.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if sub_key in flat:
                    raise ConfigError(f"duplicate key {sub_key!r} in config")
                flat[sub_key] = sub_value
        else:
            flat[key] = value
    return flat


def load_params(path: str | Path) -> Params:
    """Load a TOML config; sections are flattened and every key must be a Params field."""
    with open(path, "rb") as handle:
        data = tomllib.load(handle)
    flat = _flatten(data)
    known = {f.name for f in fields(Params)}
    unknown = sorted(set(flat) - known)
    if unknown:
        raise ConfigError(f"unknown config keys: {', '.join(unknown)}")
    params = Params(**flat)
    problems = params.validate()
    if problems:
        raise ConfigError("invalid config:\n  " + "\n  ".join(problems))
    return params
