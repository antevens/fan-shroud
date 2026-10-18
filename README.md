# PCIe Card Fan Shroud

A 3D-printable, fully parametric shroud that clips onto a stack of passively cooled server network cards
and forces a 60 mm fan's airflow lengthwise through their heatsinks. Every dimension comes from
`configs/default.toml`; nothing is hard-coded in the geometry.

The layout follows the real machine. On the Supermicro H12DSi-N6 the GPU in SLOT6 (XFX MERC310
RX 7900 XT) blocks SLOT5 and SLOT4, leaving SLOT3, SLOT2 and SLOT1 for the NICs. There are only 78 mm
between the GPU's underside and the midplate, and the PSU cables sit close to the card tails, so an
80 mm fan with a separate duct does not fit. Instead the default `card_clip` build is one printed shroud:

- a side wall along the card top edges with one pocket per card, each holding a TPU grip pushed onto
  that card's top PCB edge;
- a bottom plate under the lowest card, 24 mm below its PCB to clear its heatsink;
- a tail end wall just past the longest card (170 mm, in the top slot), with a 60 mm fan bolted
  straight onto it;
- one rib per card at the bracket end, running along the wall's outer face to its edge and then angled
  up to an ear under that card's bracket screw, so the bracket screws hold the cards and the shroud.

The top card's PCB is the roof of the top channel, so there is no lid under the GPU and nothing touches
the midplate. The older `case` mount (floor tray pegged into the midplate plus a separate 80 mm duct) is
still selectable and tested, but it does not fit this machine.

## Parts

| Part | What it does |
|---|---|
| `shroud` | Pocketed side wall, bottom plate, stub over the top card's tail, tail end wall carrying the 60 mm fan, and one bracket rib per card |
| `grip_slotN` | U-channel pushed onto the top edge of the card in slot N; TPU 72D back, TPU 95A lips, screwed from outside the wall |
| `duct`, `gasket`, `plug`, `tray`, `pin`, `cover` | `case` mount only |

The model's frame: X runs along the cards (0 at the bracket plane, negative toward the case front),
Y runs away from the motherboard surface, Z is vertical with 0 at the floor of the bottom channel. The
midplate top sits at `-midplate_gap`.

## Build

```bash
python -m venv .venv && source .venv/bin/activate
pip install build123d trimesh rtree pytest
python -m duct.build --config configs/default.toml --coupons --print-dir print
pytest
```

Outputs land in `out/`: one `.3mf` per part, one `.stl` per part in the model frame, the print-oriented
meshes in `out/oriented/`, `assembly.step` with every part in place, and `PRINTING.md` with quantities,
orientations, materials and slicer settings. `--coupons` adds the fit prints (tail fan mount, grip and
pocket). `--print-dir print` refreshes `print/` with just the files needed at the printer: the 3MF of
every part in the current build, `PRINTING.md`, and the coupons in `print/coupons/`.

Every `.3mf` is a project file written by ElegooSlicer itself, not a bare mesh container: the build
hands the slicer CLI the oriented STL of each body with its filament, and the slicer saves the project
with the Centauri Carbon 2 printer, the process and the filament presets embedded. Two-material parts
(the grips) come out as one object with two parts on filaments 1 and 2, placed exactly as modelled.
ElegooSlicer opens these without the "not from ElegooSlicer, geometry only" warning and keeps every
setting. The build needs `elegooslicer` on the PATH for this step and refuses `--print-dir` without it.

The build warns while any key listed under `[todo].unmeasured` is still a placeholder.

`elegooslicer` (installed in `/usr/local/bin`) runs the ElegooSlicer AppImage headless. The slicing
driver slices every project in `print/` with its embedded settings (process overrides in
`configs/slicer_overrides.json` for ABS and `configs/slicer_overrides_tpu.json` for TPU) and fails on
any slicer warning such as floating regions:

```bash
python -m duct.slice --print-dir print
elegooslicer --info print/shroud.3mf
```

Sliced projects and gcode land in `out/sliced/<part>/`.

## Measurements to take

`MEASURE.md` is the checklist for the caliper session: what to measure, how, and which key it fills.
Fill the values into `configs/default.toml` and remove each key from `[todo].unmeasured` once measured.

## Fan choice

The shroud turns the fan into a pressurised source, so rated static pressure (mmH2O) matters more than
CFM. Any 60 x 60 mm fan with the standard 50 mm hole spacing fits; `tail_fan_depth` covers 15 mm slim
fans too.

| Fan | Static pressure | Note |
|---|---|---|
| Noctua NF-A6x25 PWM | 2.18 mmH2O, 17.2 CFM at 3000 rpm | Quiet (19.3 dB(A)), close to the NF-A8's pressure |
| Server fans (Delta, Sanyo Denki San Ace 60) | see datasheet | Much more pressure, loud at full speed |

## Fan control on the Supermicro H12DSi-N6

The board controls fans by zone. `FAN1` to `FAN6` are zone 0 (CPU and system), `FANA` and `FANB`
are zone 1 (peripheral). Put the shroud fan on `FANA` or `FANB` so it can run its own duty cycle.

The BMC applies lower-critical RPM thresholds. A fan that idles below its threshold trips the sensor
and the BMC cycles every fan to full speed. Lower the thresholds for the shroud fan header first:

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

Some of the cards have solid brackets, so the air cannot leave through the back of the case. The
shroud's wall and bottom plate stop `exhaust_gap` (20 mm) short of the brackets. Only the bracket ribs
cross that gap, one 10 mm rib per card outside the wall, so air reaching the bracket end still escapes
sideways toward the side panel and up toward the top exhaust fans.

The GPU's fans draw their air from below. Over the NICs the shroud adds nothing above the top card's
PCB, and the 60 mm fan sits about 11 mm under the GPU, so the GPU keeps its intake.

## Printing

See `print/PRINTING.md` for the per-part table and slicer settings. Materials on hand are PLA, ABS,
TPU 95A and Elegoo TPU 72D (Shore D, so harder than the 95A). Use ABS for the shroud: the case air can
reach 80 to 90 C at worst and PLA softens. The shroud prints standing on its tail end wall with no
supports. CANVAS feeds TPU, so the two-material grips print in one job with both TPU spools loaded:
72D for the stiff back, 95A for the lips.

## Installation (`card_clip`)

1. Push each grip onto its card's top edge, tail end `grip_margin` (4 mm) from the card tail. The lips
   reach `grip_engagement` (2.5 mm) down each face and are printed in TPU 95A, so they mould over the
   small parts the Dell card carries near its edge; the 72D back keeps the grip stiff and holds the
   screws.
2. On the bench, hold the 60 mm fan against the outer face of the shroud's tail end wall, airflow arrow
   pointing into the shroud, and drive its four standard fan screws from inside the shroud through the
   wall into the fan frame's own holes. The shroud is open on the motherboard side, so the screws are
   easy to reach before it goes in.
3. Loosen the bracket screws of the three NICs.
4. Slide the shroud in from the side panel: the bottom plate passes under the lowest card, each pocket
   closes over its grip, and each rib's ear slides under its card's bracket screw. Push until the grip
   backs touch the wall, then tighten the bracket screws. The ear adds 2 mm under each screw head, so
   the screws may need to be that much longer.
5. Drive an M2.5 x 6 mm screw through each wall hole into the grip behind it, at 55, 100 and 145 mm from
   the brackets. The holes sit at fixed distances, so they line up with any card; a short card's grip
   simply skips the positions it does not reach.

With `mount_style = "case"` the tray is pegged into the midplate first, the duct's mount bar drops into
its groove, and the cover slides in from the side.

## Status

- Done: one-piece card-clip shroud with the 60 mm tail fan wall, bracket ribs and TPU edge grips;
  the case mount with its duct, tray, pegs and cover; exports, slicer-written print projects, tests.
- Waiting on measurements: the bracket screw positions (`bracket_tab_y`, `bracket_screw_x`,
  `bracket_screw_dz`), the free length past the card tails, the two lower cards' lengths and heights,
  and the midplate and GPU positions that split the measured 78 mm.
- Not built: `booster = "side_cover_120"`, part splitting (no part exceeds the 256 mm bed).
