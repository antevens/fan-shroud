# Measurement checklist

The caliper session is the last step before printing. Everything else is done first:

1. Print and test the fit coupons (`python -m duct.build --coupons --print-dir print`, then open
   `print/coupons/coupon_*.3mf`).
   The grip coupon goes onto any spare 1.57 mm PCB edge; the pocket coupon takes the grip coupon.
   Adjust `grip_interference` and `pocket_clearance` until both feel right.
2. Have on hand: the 80 mm Noctua (25 mm deep), four M3 x 5 mm heat-set inserts (4 mm bore) and
   four M3 x 35 mm screws with washers for the fan, six standard fan screws for the duct-to-shroud
   joint, nine M2.5 x 6 mm pan-head screws for the grips,
   CA glue, both TPU spools (72D for grip backs, 95A for lips and gasket).
3. Measure (below), edit `configs/default.toml`, empty `[todo].unmeasured`, then:

```bash
python -m duct.build --config configs/default.toml --coupons --print-dir print
pytest
python -m duct.slice --out out
```

Print from `print/<part>.3mf` (ElegooSlicer projects with presets and the grips' two filaments already
set), or use the sliced projects in `out/sliced/<part>/`.

## With the side panel off, machine running

| Value | How | Key |
|---|---|---|
| Midplate gap | Ruler from the midplate top to the card opening of the SLOT1 connector | `bottom_slot_pcb_to_midplate` |
| GPU shroud underside | Gap between the SLOT3 card's PCB back and the GPU's fan shroud, measured near the card tail. Key = 60.96 minus that gap minus 0.8 | `gpu_underside_below_pcb` |
| Cables in front of the card tails | From the longest card's tail toward the case front: how far is the first obstacle (cable bundle, cutout edge) between the midplate and the GPU? The fan intake needs `free_length_from_outlet` of at least the duct length plus 20 mm, currently 71 mm | `free_length_from_outlet` |
| Side panel foam | Card top edge to the foam, for the record; the wall needs 4 mm | `side_clearance` |

If the midplate gap comes out under 20 mm the fan end would touch the midplate: set `fan_center_z`
higher by the shortfall and accept the smaller GPU clearance, or use `fan_size = 70`.

## Machine off, cards out, calipers

For each card (SLOT1 XZSNET X540, SLOT2 Mellanox MCX556N, SLOT3 Dell 57412):

| Value | How | Key |
|---|---|---|
| Length | Bracket flange (the face that sits against the case) to the PCB tail | `card_lengths` (bottom slot first) |
| PCB height | Bottom of the edge fingers to the top edge; only the grip backs change with it, the shroud does not | `card_pcb_heights` |
| PCB thickness | Calipers on a bare edge, expect 1.57 | `pcb_thickness` |
| Top-edge keep-out | Tallest part within `grip_engagement` (2.5 mm) of the top edge, both faces | soft lips mould over parts up to about 1 mm; lower `grip_engagement` if anything taller sits there |
| Seated height | Motherboard surface to the PCB bottom edge of a seated card, if easy to get at | `pcb_seat_offset` |

The Mellanox and the XZSNET are the ones to be careful with: NVIDIA lists no MCX556N, and X540 clones
come in short 106 x 57 mm boards as well as full 68.9 mm ones. Both cases already build and pass the
tests, so a surprise there costs a config edit, not a redesign.

## Optional, only if the `case` mount is ever used

Midplate slot perforations (`slot_length`, `slot_width`, `hole_pitch`, `hole_row_pitch_override`,
`sheet_thickness`, `perforation_origin_x/y`) and the cutouts (`cutouts`). The card-clip mount
never touches the midplate, so these can stay as placeholders.
