# Printing

Printer: Elegoo Centauri Carbon 2 Combo (256 x 256 x 256 mm, 0.4 mm nozzle).

Each `.3mf` is a project file written by ElegooSlicer itself: printer, process and filament presets are
embedded and the part is already rotated into its print orientation and centred on the bed. Open it,
check the filament mapping, slice. The `.stl` files in `out/` are in the duct frame for CAD use,
`out/oriented/` holds the print-oriented meshes and `out/assembly.step` every part in place.

## Parts

| Part | Qty | Material | Orientation | Notes |
|---|---|---|---|---|
| `shroud.3mf` (72 x 107 x 177 mm) | 1 | ABS | standing on its tail end wall, bracket end up | Slides over the gripped cards from the side panel; one pocket per card grip. The 60 mm fan bolts onto the tail end wall; each rib's ear goes under its card's PCI bracket screw. No supports; use a brim. |
| `grip_slot1.3mf` (124 x 4 x 8 mm) | 1 | TPU 72D back, TPU 95A lips | back down, channel up | Push onto the top edge of the card in SLOT1 (152 mm card), tail end 4 mm from the card tail; back 5.5 mm with 3 screw pilots. One object, two parts: `grip_slot1_back` on filament 1 (TPU 72D), `grip_slot1_lips` on filament 2 (TPU 95A). |
| `grip_slot2.3mf` (114 x 4 x 8 mm) | 1 | TPU 72D back, TPU 95A lips | back down, channel up | Push onto the top edge of the card in SLOT2 (142.24 mm card), tail end 4 mm from the card tail; back 5.5 mm with 2 screw pilots. One object, two parts: `grip_slot2_back` on filament 1 (TPU 72D), `grip_slot2_lips` on filament 2 (TPU 95A). |
| `grip_slot3.3mf` (142 x 4 x 8 mm) | 1 | TPU 72D back, TPU 95A lips | back down, channel up | Push onto the top edge of the card in SLOT3 (170 mm card), tail end 4 mm from the card tail; back 5.5 mm with 3 screw pilots. One object, two parts: `grip_slot3_back` on filament 1 (TPU 72D), `grip_slot3_lips` on filament 2 (TPU 95A). |

## Fit coupons

| Coupon | Purpose |
|---|---|
| `coupon_fan_mount.3mf` | The tail end wall: screw the 60 mm fan on with its own fan screws from the inside; the frame must sit square and the screws bite. |
| `coupon_grip.3mf` | 30 mm grip built like the real ones: TPU 72D back on filament 1, TPU 95A lips on filament 2 from Z = 5.5 mm. Push it onto any spare 1.57 mm PCB edge, then pull on the lips to check the two TPUs bonded. Adjust `grip_interference` if the fit is off. |
| `coupon_pocket.3mf` | Wall slice with one pocket: the grip coupon should slide in with light friction and its back touch the pad. Adjust `pocket_clearance` if not. |

## Slicer settings (ElegooSlicer)

Every project already carries these, so there is nothing to set by hand:

- Printer: `Elegoo Centauri Carbon 2 0.4 nozzle`.
- Filaments: `Elegoo ABS @ECC2` for the rigid parts, `Elegoo TPU 95A @ECC2` for TPU 95A and `Elegoo TPU 72D @ECC2` for TPU 72D. ElegooSlicer ships no 72D preset, so that one is derived from the 95A preset with Elegoo's 72D temperatures (230 C nozzle, 40 C bed, `configs/filament_tpu72d.json`) and travels inside the project.
- Process: `0.20mm Standard @Elegoo CC2 0.4 nozzle` with 4 wall loops (1.6 mm, the configured minimum wall is 1.6 mm), 20 % gyroid infill, 4 top and bottom layers, 5 mm outer brim and no supports (`configs/slicer_overrides.json`); TPU parts get 100 % infill and no brim (`configs/slicer_overrides_tpu.json`).

At the printer:

- ABS: the preset sets 270 C nozzle, 90 C bed on the textured PEI plate and a 5 mm brim on the shroud. The chamber has no heater: close the door and louvres, start the bed and let it warm the chamber for 10 minutes before the print begins, watching the printer's chamber readout.
- Fan: a 60 mm fan (50 mm hole spacing), airflow arrow pointing into the shroud. Before the shroud goes on, hold the fan against the tail end wall's outer face and drive its four standard 10 mm fan screws from inside the shroud, through the wall into the fan frame's own holes; reach them from the shroud's open motherboard side.
- Bracket tab: loosen the screws of the covered cards' brackets, slide the tab under their heads, retighten. The tab adds 2 mm under each head, so the screws may need to be that much longer.
- TPU: feed it through CANVAS like any other spool; dry the 72D first (70 C, 8 h) if the spool has been open.
- Grips: one object with two parts, the back on filament 1 (TPU 72D) and the lips on filament 2 (TPU 95A). Map the two filaments to the CANVAS slots holding those spools and the printer swaps by itself; with one spool, point both filaments at it and add a filament change at Z = 5.5 mm. Both are TPU, so the lips bond to the back like any other layer.
