"""The model must build for the measurement ranges expected from the caliper session."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from duct.build import build_parts
from duct.params import load_params

CONFIG = Path(__file__).resolve().parent.parent / "configs" / "default.toml"

VARIANTS = {
    "short_low_x540_clone": dict(card_lengths=[106.5, 142.24, 167.64], card_pcb_heights=[57.0, 68.9, 68.9]),
    "mellanox_half_length": dict(card_lengths=[152.0, 167.65, 167.64]),
    "all_cards_68mm": dict(card_pcb_heights=[68.1, 68.9, 68.6]),
    "midplate_gap_20": dict(bottom_slot_pcb_to_midplate=36.0),
    "midplate_gap_40": dict(bottom_slot_pcb_to_midplate=56.0),
    "gpu_shroud_lower": dict(gpu_underside_below_pcb=54.0),
    "gpu_shroud_higher": dict(gpu_underside_below_pcb=48.0),
    "fan_25mm": dict(fan_depth=25.0),
    "grip_3mm": dict(grip_engagement=3.0),
    "grip_1p5mm": dict(grip_engagement=1.5),
    "pcb_1p6": dict(pcb_thickness=1.6),
    "short_card_wall_pads": dict(card_lengths=[106.5, 142.24, 167.64], card_pcb_heights=[57.0, 68.9, 68.9], grip_fill="wall"),
}


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_variant_validates_and_builds(name):
    params = dataclasses.replace(load_params(CONFIG), **VARIANTS[name])
    assert params.validate() == [], params.validate()
    parts = build_parts(params)
    for part_name, item in parts.items():
        assert item.part.is_valid, f"{name}: {part_name} invalid"
        assert len(item.part.solids()) == 1, f"{name}: {part_name} is not one solid"
    limit = params.gpu_plane_z - params.gpu_top_clearance + 1e-6
    assert parts["duct"].part.bounding_box().max.Z <= limit
    assert parts["shroud"].part.bounding_box().max.Z <= limit
    assert parts["duct"].part.bounding_box().min.Z >= params.midplate_z - 1e-6
