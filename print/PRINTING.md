# Printing

Printer: Elegoo Centauri Carbon 2 Combo (256 x 256 x 256 mm, 0.4 mm nozzle).

Each `.3mf` is a project file written by ElegooSlicer itself: printer, process and filament presets are
embedded and the part is already rotated into its print orientation and centred on the bed. Open it,
check the filament mapping, slice. The `.stl` files in `out/` are in the duct frame for CAD use,
`out/oriented/` holds the print-oriented meshes and `out/assembly.step` every part in place.

## Parts

| Part | Qty | Material | Orientation | Notes |
|---|---|---|---|---|
| `shroud.3mf` (72 x 109 x 177 mm) | 1 | ABS | standing on its tail end wall, bracket end up | Carries the grips in its dovetail grooves and goes onto the cards with them from the side panel. The 60 mm fan bolts onto the tail end wall; each rib's ear goes under its card's PCI bracket screw. No supports; use a brim. |
| `grip_slot1.3mf` (124 x 7 x 8 mm) | 1 | TPU 95A | back down, channel up | Slides into groove 1 (counted from the bottom plate) from the shroud's bracket end until its end sits 4 mm inside the edge, then goes onto the top edge of the card in SLOT1 (152 mm card) with the shroud. Back 5.5 mm with a 7.3 mm dovetail key. |
| `grip_slot2.3mf` (114 x 7 x 8 mm) | 1 | TPU 95A | back down, channel up | Slides into groove 2 (counted from the bottom plate) from the shroud's bracket end until its end sits 4 mm inside the edge, then goes onto the top edge of the card in SLOT2 (142.24 mm card) with the shroud. Back 5.5 mm with a 7.3 mm dovetail key. |
| `grip_slot3.3mf` (142 x 7 x 8 mm) | 1 | TPU 95A | back down, channel up | Slides into groove 3 (counted from the bottom plate) from the shroud's bracket end until its end sits 4 mm inside the edge, then goes onto the top edge of the card in SLOT3 (170 mm card) with the shroud. Back 5.5 mm with a 7.3 mm dovetail key. |

## Fit coupons

| Coupon | Purpose |
|---|---|
| `coupon_fan_mount.3mf` | The tail end wall: screw the 60 mm fan on with its own fan screws from the inside; the frame must sit square and the screws bite. |
| `coupon_grip.3mf` | 30 mm grip in TPU 95A, built like the real ones. Push it onto any spare 1.57 mm PCB edge; adjust `grip_interference` if the fit is off. |
| `coupon_pocket.3mf` | Wall slice with one dovetail groove, printed standing like the shroud: the grip coupon's key should slide in from either end with light friction and not pull out toward the card. Adjust `pocket_clearance` if it binds or rattles, `dovetail_angle` if it pulls out. |

## Slicer settings (ElegooSlicer)

Every project already carries these, so there is nothing to set by hand:

- Printer: `Elegoo Centauri Carbon 2 0.4 nozzle`.
- Filaments: `Elegoo ABS @ECC2` for the rigid parts and `Elegoo TPU 95A @ECC2` for the grips.
- Process: `0.20mm Standard @Elegoo CC2 0.4 nozzle` with 4 wall loops (1.6 mm, the configured minimum wall is 1.6 mm), 20 % gyroid infill, 4 top and bottom layers, 5 mm outer brim and no supports (`configs/slicer_overrides.json`); TPU parts get 100 % infill and no brim (`configs/slicer_overrides_tpu.json`).

At the printer:

- ABS: the preset sets 270 C nozzle, 90 C bed on the textured PEI plate and a 5 mm brim on the shroud. The chamber has no heater: close the door and louvres, start the bed and let it warm the chamber for 10 minutes before the print begins, watching the printer's chamber readout.
- Fan: a 60 mm fan (50 mm hole spacing), airflow arrow pointing into the shroud. Before the shroud goes on, hold the fan against the tail end wall's outer face and drive its four standard 10 mm fan screws from inside the shroud, through the wall into the fan frame's own holes; reach them from the shroud's open motherboard side.
- Bracket tab: loosen the screws of the covered cards' brackets, slide the tab under their heads, retighten. The tab adds 2 mm under each head, so the screws may need to be that much longer. Ridges along both long edges of each rib stop short of the screw head (8 mm clearance).
- TPU: feed it through CANVAS like any other spool; dry it first if the spool has been open.
- Grips: one TPU 95A body each, printed back down so the dovetail key's wide face is on the plate. Slide each into its groove from the shroud's bracket end, SLOT1's grip into the groove next to the bottom plate, before the shroud goes onto the cards.
