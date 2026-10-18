# Measurement checklist

The caliper session is the last step before printing. Everything else is done first:

1. Print and test the fit coupons (`python -m duct.build --coupons --print-dir print`, then open
   `print/coupons/coupon_*.3mf`).
   The fan mount coupon takes the 60 mm fan with its own screws. The grip coupon goes onto any spare
   1.57 mm PCB edge; the pocket coupon takes the grip coupon. Adjust `grip_interference` and
   `pocket_clearance` until both feel right.
2. Have on hand: the 60 mm fan with its four fan screws, nine M2.5 x 6 mm pan-head screws for the
   grips, three bracket screws about 2 mm longer than the current ones, and both TPU spools (72D for
   grip backs, 95A for lips).
3. Measure (below), edit `configs/default.toml`, empty `[todo].unmeasured`, then:

```bash
python -m duct.build --config configs/default.toml --coupons --print-dir print
pytest
python -m duct.slice --print-dir print
```

Print from `print/<part>.3mf` (ElegooSlicer projects with presets and the grips' two filaments already
set), or use the sliced projects in `out/sliced/<part>/`.

## Already measured

| Value | Result | Key |
|---|---|---|
| GPU underside to midplate | 78 mm | split between the two keys below |
| Longest card, SLOT3 Dell 57412 | 170 mm from the bracket | `card_lengths` (last entry) |
| Bottom plate depth | 8 mm more than the CEM default, for the bottom card's heatsink | `channel_floor_below_pcb = 24` |

## With the side panel off, machine running

| Value | How | Key |
|---|---|---|
| Midplate gap | Ruler from the midplate top to the card opening of the SLOT1 connector | `bottom_slot_pcb_to_midplate` |
| GPU shroud underside | Gap between the SLOT3 card's PCB back and the GPU's fan shroud, near the card tail. Key = 60.96 minus that gap minus 0.8. With the midplate gap it must add up to the 78 mm | `gpu_underside_below_pcb` |
| Cables past the card tails | From the 170 mm card's tail toward the case front: distance to the first cable or edge between the midplate and the GPU. The fan needs 32 mm (4 mm clearance, 3 mm wall, 25 mm fan) | `free_length_past_cards` |
| Bracket tab face | Motherboard surface to the outer face of a NIC's bracket tab, where the screw head sits | `bracket_tab_y` |
| Bracket screw position | Bracket plane (outer face of the bracket) to the screw axis, inside the case is negative | `bracket_screw_x` |
| Screw height | Each NIC's bracket screw axis relative to that card's PCB plane, along the slot stack | `bracket_screw_dz` |
| Side panel foam | Card top edge to the foam, for the record | `side_clearance` |

## Machine off, cards out, calipers

For each card (SLOT1 XZSNET X540, SLOT2 Mellanox MCX556N, SLOT3 Dell 57412):

| Value | How | Key |
|---|---|---|
| Length | Bracket flange (the face that sits against the case) to the PCB tail | `card_lengths` (bottom slot first) |
| PCB height | Bottom of the edge fingers to the top edge; only the grip backs change with it, the shroud does not | `card_pcb_heights` |
| PCB thickness | Calipers on a bare edge, expect 1.57 | `pcb_thickness` |
| Top-edge keep-out | Tallest part within `grip_engagement` (2.5 mm) of the top edge, both faces | soft lips mould over parts up to about 1 mm; lower `grip_engagement` if anything taller sits there |
| Seated height | Motherboard surface to the PCB bottom edge of a seated card, if easy to get at | `pcb_seat_offset` |

The tail wall sits just past the longest card. If one of the lower cards turns out longer than the
170 mm top card, the wall moves back with it and the build reports the new fan position.

## Optional, only if the `case` mount is ever used

Midplate slot perforations (`slot_length`, `slot_width`, `hole_pitch`, `hole_row_pitch_override`,
`sheet_thickness`, `perforation_origin_x/y`), the cutouts (`cutouts`) and `free_length_from_outlet`.
The card-clip shroud never touches the midplate, so these can stay as placeholders.
