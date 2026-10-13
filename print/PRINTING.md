# Printing

Printer: Elegoo Centauri Carbon 2 Combo (256 x 256 x 256 mm, 0.4 mm nozzle).

Each `.3mf` is a project file written by ElegooSlicer itself: printer, process and filament presets are
embedded and the part is already rotated into its print orientation and centred on the bed. Open it,
check the filament mapping, slice. The `.stl` files in `out/` are in the duct frame for CAD use,
`out/oriented/` holds the print-oriented meshes and `out/assembly.step` every part in place.

## Parts

| Part | Qty | Material | Orientation | Notes |
|---|---|---|---|---|
| `duct.3mf` (82 x 84 x 26 mm) | 1 | ABS | outlet face down, fan flange up | No supports; the converging walls overhang up to 39 deg. Brim recommended for ABS. |
| `plug.3mf` (68 x 20 x 20 mm) | 3 | ABS | wedge down, plate and handle up | One per empty slot channel; print only what you need. |
| `gasket.3mf` (75 x 84 x 3 mm) | 1 | TPU 95A | flat | Soft TPU between the duct's outlet frame and the shroud flange or card tails. |
| `shroud.3mf` (76 x 84 x 150 mm) | 1 | ABS | standing on its tail flange, exhaust end up | Slides over the gripped cards from the side panel; one pocket per card grip. No supports; use a brim. Standard fan screws go through the bars on its flange into the duct. |
| `grip_slot1.3mf` (124 x 4 x 8 mm) | 1 | TPU 72D back, TPU 95A lips | back down, channel up | Push onto the top edge of the card in SLOT1 (152 mm card), tail end 4 mm from the card tail; back 5.5 mm with 3 screw pilots. One object, two parts: `grip_slot1_back` on filament 1 (TPU 72D), `grip_slot1_lips` on filament 2 (TPU 95A). |
| `grip_slot2.3mf` (114 x 4 x 8 mm) | 1 | TPU 72D back, TPU 95A lips | back down, channel up | Push onto the top edge of the card in SLOT2 (142.24 mm card), tail end 4 mm from the card tail; back 5.5 mm with 3 screw pilots. One object, two parts: `grip_slot2_back` on filament 1 (TPU 72D), `grip_slot2_lips` on filament 2 (TPU 95A). |
| `grip_slot3.3mf` (140 x 4 x 8 mm) | 1 | TPU 72D back, TPU 95A lips | back down, channel up | Push onto the top edge of the card in SLOT3 (167.64 mm card), tail end 4 mm from the card tail; back 5.5 mm with 3 screw pilots. One object, two parts: `grip_slot3_back` on filament 1 (TPU 72D), `grip_slot3_lips` on filament 2 (TPU 95A). |

## Fit coupons

| Coupon | Purpose |
|---|---|
| `coupon_fan_flange.3mf` | Press the M3 inserts, bolt the fan on, check the 80 mm frame seat. |
| `coupon_outlet_corner.3mf` | Check the gasket lip and wall thickness. |
| `coupon_grip.3mf` | 30 mm grip built like the real ones: TPU 72D back on filament 1, TPU 95A lips on filament 2 from Z = 5.5 mm. Push it onto any spare 1.57 mm PCB edge, then pull on the lips to check the two TPUs bonded. Adjust `grip_interference` if the fit is off. |
| `coupon_pocket.3mf` | Wall slice with one pocket: the grip coupon should slide in with light friction and its back touch the pad. Adjust `pocket_clearance` if not. |

## Slicer settings (ElegooSlicer)

Every project already carries these, so there is nothing to set by hand:

- Printer: `Elegoo Centauri Carbon 2 0.4 nozzle`.
- Filaments: `Elegoo ABS @ECC2` for the rigid parts, `Elegoo TPU 95A @ECC2` for TPU 95A and `Elegoo TPU 72D @ECC2` for TPU 72D. ElegooSlicer ships no 72D preset, so that one is derived from the 95A preset with Elegoo's 72D temperatures (230 C nozzle, 40 C bed, `configs/filament_tpu72d.json`) and travels inside the project.
- Process: `0.20mm Standard @Elegoo CC2 0.4 nozzle` with 4 wall loops (1.6 mm, the configured minimum wall is 1.6 mm), 20 % gyroid infill, 4 top and bottom layers, 5 mm outer brim and no supports (`configs/slicer_overrides.json`); TPU parts get 100 % infill and no brim (`configs/slicer_overrides_tpu.json`).

At the printer:

- ABS: close the door, bed 100 C, brim 5 mm on the duct and shroud, let the chamber warm for 10 minutes first.
- Duct to shroud: gasket between the two flanges, 6 standard self-tapping fan screws from the shroud side through the thin bars on its flange and the gasket into the 4.3 mm holes in the duct's thick bars: four along the bottom edge, two up the side-panel edge.
- Fan: press four M3 x 5 mm heat-set inserts (4 mm bore) into the flange's corner pads from the fan face, then mount the fan with M3 x 34 mm screws and washers through its frame. The fan's own corner pads seal it to the flange; no gasket there.
- TPU: feed it through CANVAS like any other spool; dry the 72D first (70 C, 8 h) if the spool has been open.
- Grips: one object with two parts, the back on filament 1 (TPU 72D) and the lips on filament 2 (TPU 95A). Map the two filaments to the CANVAS slots holding those spools and the printer swaps by itself; with one spool, point both filaments at it and add a filament change at Z = 5.5 mm. Both are TPU, so the lips bond to the back like any other layer.

## Gaskets

- Joint gasket: `gasket.3mf`, 2.5 mm TPU 95A, clamped between the duct and shroud flanges by the fan screws; no glue. 3 mm foam tape is the fallback.
