# PCIe Card Fan Duct

A 3D-printable, fully parametric duct that mounts a slim 80 mm fan at the tail end of a stack of passively
cooled server network cards and forces its airflow lengthwise through their heatsinks. Every dimension
comes from `configs/default.toml`; nothing is hard-coded in the geometry.

The current layout follows the real machine: on the Supermicro H12DSi-N6 the GPU in SLOT6 (XFX MERC310
RX 7900 XT, 344 x 128 x 55 mm) blocks SLOT5 and SLOT4, leaving SLOT3, SLOT2 and SLOT1 as three low-profile
channels. The fan converges into them and its intake sits 56 mm past the longest card, clear of the midplate
cable cutout. The default mount is `card_clip`: a soft TPU grip is pushed onto each card's top PCB edge, and
a pocketed side wall with a bottom plate slides over the grips. The top card's PCB is the roof of the top
channel, so there is no lid under the GPU and nothing touches the midplate. The `case` mount (floor tray
pegged into the midplate plus a separate cover) is still selectable.

## Parts

| Part | What it does |
|---|---|
| `duct` | Fan flange, converging transition, per-slot splitter vanes and outlet gasket frame (optional pinned foot) |
| `shroud` | `card_clip`: side wall with one pocket per card, bottom plate, a stub over the top card's tail, and a tail flange with screw bars on its bottom and side-panel edges that the duct bolts to |
| `grip_slotN` | `card_clip`: U-channel pushed onto the top edge of the card in slot N; TPU 72D back, TPU 95A lips, screwed from outside the wall |
| `plug` | Blanking wedge that closes one channel when its slot is empty |
| `gasket` | Soft TPU frame between the duct's outlet frame and the shroud flange |
| `tray` | `case`: thin floor tray that seals the midplate perforations; its upstand carries the groove the duct's mount bar drops into |
| `pin` | `case`: press-in pegs shaped to the midplate slots that lock the tray down |
| `cover` | `case`: lid under the GPU plus a side wall along the card top edges |

The duct's frame: X runs along the cards (0 at the bracket plane, negative toward the case front),
Y runs away from the motherboard surface, Z is vertical with 0 at the floor of the bottom-most covered
channel. The midplate top sits at `-midplate_gap`.

## Build

```bash
python -m venv .venv && source .venv/bin/activate
pip install build123d trimesh rtree pytest
python -m duct.build --config configs/default.toml --coupons --print-dir print
pytest
```

Outputs land in `out/`: one `.3mf` per part, one `.stl` per part in the duct frame, the print-oriented
meshes in `out/oriented/`, `assembly.step` with every part in place, and `PRINTING.md` with quantities,
orientations, materials and slicer settings. `--coupons` adds the fit prints (fan flange, outlet
corner, grip and pocket). `--print-dir print` refreshes `print/` with just the files needed at the
printer: the 3MF of every part in the current build, `PRINTING.md`, and the coupons in `print/coupons/`.

Every `.3mf` is a project file written by ElegooSlicer itself, not a bare mesh container: the build
hands the slicer CLI the oriented STL of each body with its filament, and the slicer saves the project
with the Centauri Carbon 2 printer, the process and the filament presets embedded. Two-material parts
(the grips) come out as one object with two parts on filaments 1 and 2, placed exactly as modelled.
ElegooSlicer opens these without the "not from ElegooSlicer, geometry only" warning and keeps every
setting. The build needs `elegooslicer` on the PATH for this step and refuses `--print-dir` without it.

The build warns while any key listed under `[todo].unmeasured` is still a placeholder.

`elegooslicer` (installed in `/usr/local/bin`) runs the ElegooSlicer AppImage headless. The slicing
driver slices every project in `print/` with its embedded settings (the process overrides come from
`configs/slicer_overrides.json`, 4 walls, 20 % gyroid, brim, no supports, and
`configs/slicer_overrides_tpu.json` for the TPU parts) and fails on any slicer warning such as floating
regions:

```bash
python -m duct.slice --print-dir print
elegooslicer --info print/duct.3mf
```

Sliced projects and gcode land in `out/sliced/<part>/`.

## Measurements to take

`MEASURE.md` is the checklist for the caliper session: what to measure, how, and which key it fills.
Fill the values into `configs/default.toml` and remove each key from `[todo].unmeasured` once measured.

| Key | How to measure |
|---|---|
| `bottom_slot_pcb_to_midplate` | Midplate top to the card opening of the SLOT1 connector. Sets how far the fan end may hang below the bottom channel. |
| `gpu_underside_below_pcb` | GPU PCB plane down to the lowest point of its fan shroud. 52 mm assumed from the 55 mm card thickness. |
| `card_lengths` | Per slot, bottom first: tail of each card from the bracket plane. The Dell 57412 is half-length (167.64 mm); NVIDIA lists the MCX556A family at 142.24 mm but not the MCX556N; the XZSNET X540 clone has no published size. |
| `card_pcb_heights` | Per slot: PCB height from the bottom of the edge fingers to the top edge. The wall sits at the 68.9 mm low-profile reference; a shorter card only gets a grip with a taller back. |
| `cutouts` | Each midplate cutout as `[x0, x1, y0, y1]`: X from the bracket plane (negative), Y from the motherboard. Pegs avoid them and the build refuses a foot on one. |
| `free_length_from_outlet` | Free length in front of the outlet plane before cables or the cutout. The fan intake needs `transition + flange + fan depth + 20 mm`, currently 59 mm. |
| `side_clearance` | Top edge of a low-profile card to the damping foam on the side panel. |
| `under_midplate_gap` | Gap between the midplate and the PSU. |
| `slot_length`, `slot_width`, `hole_pitch`, `hole_row_pitch_override`, `sheet_thickness` | Midplate slot perforations: slot size, spacing along a row, row spacing, sheet thickness. Rows are staggered by half a pitch. |
| `perforation_origin_x`, `perforation_origin_y` | Centre of any one slot: X from the bracket plane (negative), Y from the motherboard surface. Pegs are placed on this grid. |

Print `coupon_pin_sizing.3mf` once the slot size is known: it carries five pegs, each 0.1 mm
smaller than the last. Set `peg_clearance` to the first one that presses in by hand.

## Fan choice

The duct turns the fan into a pressurised source, so rated static pressure (mmH2O) matters more than
CFM. Pick an 80 mm PWM fan with the highest static pressure you can tolerate for noise:

| Fan | Static pressure | Note |
|---|---|---|
| Arctic P8 Max | 5.3 mmH2O at 5000 rpm | Good pressure, PWM down to 500 rpm |
| Noctua NF-A8 PWM | 2.37 mmH2O | Quiet but too little pressure for a sealed duct |
| Server fans (Delta, Sanyo Denki San Ace 80) | see datasheet | Highest pressure, loud at full speed |

## Fan control on the Supermicro H12DSi-N6

The board controls fans by zone. `FAN1` to `FAN6` are zone 0 (CPU and system), `FANA` and `FANB`
are zone 1 (peripheral). Put the duct fan on `FANA` or `FANB` so it can run its own duty cycle.

The BMC applies lower-critical RPM thresholds. A fan that idles below its threshold trips the sensor
and the BMC cycles every fan to full speed. Lower the thresholds for the duct fan header first:

```bash
# lower non-recoverable, lower critical, lower non-critical
ipmitool sensor thresh FANA lower 100 200 300
```

Then set the zone duty cycle (0 to 100) after putting the BMC in full mode so it stops overriding:

```bash
ipmitool raw 0x30 0x45 0x01 0x01        # fan mode: full
ipmitool raw 0x30 0x70 0x66 0x01 0x01 0x40   # zone 1 (peripheral) to 64 %
ipmitool raw 0x30 0x70 0x66 0x00 0x01        # read back zone 1 duty
```

Thresholds reset when the BMC reboots; re-apply them from a boot script.

## Exhaust gap

Some of the cards have solid brackets, so the air cannot leave through the back of the case. Nothing
the duct adds encloses the last `exhaust_gap` (20 mm) of the slot area before the brackets: the tray
and the cover stop there, and the tail duct ends at the card tails. Air reaching the bracket end escapes
sideways toward the side panel and up toward the top exhaust fans.

The GPU's fans draw their air from the slot area below them and push it out through the card's edges
and vented tail. The cover lid sits 1.5 mm under the GPU shroud over the NIC area, so the GPU's rear fan
draws from the open space beyond the lid, not from the plenum.

## Printing

See `print/PRINTING.md` for the per-part table and slicer settings. Materials on hand are PLA, ABS,
TPU 95A and Elegoo TPU 72D (Shore D, so harder than the 95A). Use ABS for the rigid parts: the GPU's
exhaust heats the duct and PLA softens. Print the gasket in TPU 95A, the softest grade on hand, so it
conforms between the two flanges. CANVAS feeds TPU, so the two-material grips print in one job with both
TPU spools loaded: 72D for the stiff back, 95A for the lips.

## Installation (`card_clip`)

1. Push each grip onto its card's top edge, tail end `grip_margin` (4 mm) from the card tail. The lips
   reach `grip_engagement` (2.5 mm) down each face and are printed in TPU 95A (a second object in the
   grip's 3MF, or a filament change at the height given in `print/PRINTING.md` with one spool), so they
   mould over the small parts the Dell card carries near its edge; the 72D back keeps the grip stiff
   and holds the screws.
2. Press four M3 x 5 mm heat-set inserts into the flange's corner pads from the fan face and bolt
   the Noctua on with M3 x 35 mm screws and washers, airflow arrow pointing into the duct. Its own
   corner pads do the sealing.
3. Fit a blanking plug into every channel whose slot is empty, from the outlet side.
4. Join duct and shroud on the bench: gasket between the two flanges, then six standard fan screws
   from the shroud side through the bars on its flange and the gasket into the 4.3 mm holes in the
   duct's thick bars, exactly as a fan screw bites into a fan frame: four along the bottom edge, two
   up the side-panel edge. The top edge has no room under the GPU and the motherboard edge only 5 mm,
   so those two edges are held by the frames' stiffness between the screwed edges.
5. Slide the assembly in from the side panel: the bottom plate passes under the lowest card and each
   pocket closes over its grip. Push until the grip backs touch the wall. The gasket face ends up 5 mm
   from the longest card's tail.
6. Drive an M2.5 x 6 mm screw through each wall hole into the grip behind it: three per grip at 35,
   85 and 135 mm from the brackets. The holes sit at fixed distances, so they line up with any card;
   a short card's grip simply skips the positions it does not reach.

With `mount_style = "case"` the tray is pegged into the midplate first, the duct's mount bar drops into
its groove, and the cover slides in from the side.

## Status

- Done: parameters and config loading, fan flange, converging transition with auto-length, splitter
  vanes, outlet gasket frame, blanking plugs, card-clip shroud with TPU edge grips, floor tray with slot
  pegs and cover for the case mount, exports, slicing, tests for both mount styles.
- Not built yet: `booster = "side_cover_120"` (the plenum wall is only 85 mm tall, so a 120 mm fan
  does not fit; an 80 mm cut-in is the candidate), `mount_style = "card_clip"`, part splitting (no
  part exceeds the 256 mm bed).
