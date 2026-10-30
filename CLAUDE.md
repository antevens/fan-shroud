# PCIe Card Fan Duct — Project Brief

## Goal
Design a 3D-printable, fully parametric duct that mounts an 80 mm fan at the tail end of a stack of
passively cooled server network cards in a desktop case, and forces the fan's airflow lengthwise through
the cards' heatsinks.

Server cards are built for high-static-pressure chassis airflow from the card tail toward the bracket.
Without it they throttle or overheat. The duct's job is to make the fan act like a server chassis fan:
sealed, direct and pressurized.

## Target system
- **Case:** Phanteks XT Pro Silent (PH-XT523PSC_BK01), 450 × 230 × 500 mm. It has closed **steel** side and front
  panels lined with sound-damping material; there is no window and no side fan mount. Fan locations are 3 × 120 mm
  on top, 1 × 120 mm at the rear and **3 × 120 mm on the midplate** (the PSU shroud, directly below the slot area).
  There are no front fan mounts, so the duct can't rely on front intake airflow at the card tails.
- **Case fans in use:** top and rear 120 mm only, both **exhaust** (confirmed). The midplate fan locations are
  **unusable** (no space), so the case has no intake fans. Fresh air enters through the closed panels' intake vents
  and the perforated midplate. Air leaving the slot area goes out the rear exhaust fan, the top exhaust fans, or
  through any vented brackets.
- **Perforated midplate with a bypass gap underneath:** the midplate (PSU shroud) between the PSU and the PCIe slots
  is perforated, and there is a ~15 mm gap (`under_midplate_gap`) between it and the PSU that runs the **whole length
  of the case**. That gap is a low-resistance bypass. Pressurized duct air reaching the perforations under the cards
  will dump down into it and travel away without crossing a heatsink. The bottom slot channel is most exposed, and
  with the side-cover booster the plenum floor would be the biggest leak in the system. So the midplate is split
  into zones:
  - **Intake zone (leave open):** perforations upstream of the duct, under and in front of the 80 mm fan. With
    exhaust-only case fans, air here mostly flows **up**, so the fan's intake sits low, close to the midplate, to
    draw it in (`fan_intake_offset_from_midplate`, as small as the fan frame allows).
  - **Card zone (seal):** perforations under the cards, from the duct outlet plane to `exhaust_gap` before the
    brackets. A printed **floor tray** lies flat on the midplate here and blocks them. Its edges and its joint to the
    duct's bottom wall carry a gasket lip.
  - **Exhaust zone (leave open):** the last `exhaust_gap` before the brackets, as an extra escape route.
- **Motherboard:** Supermicro H12DSi-N6 (E-ATX, 12" × 13.05"). It has 6 PCIe 4.0 slots (3 × x16, 3 × x8),
  8 × 4-pin PWM fan headers and IPMI fan control.
- **SLOT6 (top physical slot, x16):** XFX Speedster MERC310 RX 7900 XT (RX-79TMERCB9), 344 × 128 × 55 mm. This
  card is open-air with three fans and its body blocks SLOT5 and SLOT4 below it. **Do not duct it.** It overhangs
  the NIC stack, and its fans face down and draw air up from the area where the duct sits; its exhaust leaves
  through its edges and vented tail. The board's manual numbers SLOT1 (x8) at the bottom up to SLOT6 (x16) at the
  top; SLOT3 (x8), SLOT2 (x16) and SLOT1 (x8) are the usable positions below the GPU.
- **Current add-in cards** (passive; the duct must not depend on which slot each is in):
  | Bus | Card | Notes |
  |---|---|---|
  | a1:00 | Mellanox ConnectX-5 Ex (MT28800), PCIe 4.0 | Hottest card; top cooling priority. MCX556N (dual QSFP28); NVIDIA lists the MCX556A family at 142.24 × 68.90 mm, N variant unlisted, low profile |
  | 81:00 | Intel X540-AT2 dual 10GBASE-T | 10GBASE-T PHYs run hot. XZSNET X540-T2 clone, about 152 mm long (unverified), low profile |
  | 01:00 | Broadcom BCM57412 dual 10G SFP+ | SFP+ modules add heat. Dell OEM 57412 (BCM957412A4120DC, DP/N 0GMW01) re-flashed, 167.64 mm, low profile |
- **Onboard (not ducted):** Broadcom BCM5720 1GbE, ASPEED AST2600 BMC.
- **Out of scope:** Renesas uPD720201 USB controller (bus 61) and the four Intel Optane NVMe devices. They sit
  outside the duct area, so ignore them.
### Core requirement: slot-agnostic coverage
The duct must cool **every PCIe slot position below the GPU, whatever card is in it or if it is empty**.
Cards can be moved, swapped or added without reprinting. So the design never depends on which card is in which slot:
- **Outlet width** spans from just below the GPU to the bottom-most slot position:
  `slot_positions_covered × 20.32 mm` plus wall margin. The default is every position below the GPU's footprint
  (measure on the real board).
- **Outlet height** covers the full card zone, from the motherboard surface to the top of a full-height card
  (`card_zone_height`, default 111 mm). This way both low-profile and full-height cards are covered.
- **Outlet plane** sits past the longest card that fits there (`outlet_offset_from_bracket`, default 175 mm =
  half-length 167.65 mm + clearance). Shorter cards still get the airflow; the duct never collides with a longer card.
- **Splitter vanes** at every 20.32 mm slot boundary give each slot position an equal channel, so airflow
  doesn't take the easy path through empty slots.
- **Blanking plugs:** optional printed snap-in plugs close a channel for an empty slot, sending more air to the occupied ones.

### Geometry implication
Measured 2026-10-18: only **78 mm** between the GPU's underside and the midplate, the longest card (170 mm,
in the top slot) reaches almost to the PSU cables, and the bottom card's heatsink needs the bottom plate
24 mm below its PCB. An 80 mm fan does not fit, and there is no room for a separate duct, a duct-to-shroud
joint or any flange outside the fan's own outline. So the card-clip build is **one shroud** whose tail end
wall carries a **60 mm fan** (60 × 60 × 25, 50 mm hole spacing) bolted straight on with standard fan screws
from inside. With 3 slot positions × 20.32 ≈ 61 mm the fan face matches the card stack, so no transition is
needed. The rotor of the NF-A8 cannot be separated from its frame, tilted 80 mm layouts and side-mounted fans
were drawn and rejected (cables, SSDs, GPU intake).

### Fan configuration
- **Primary: 60 mm fan on the shroud's tail end wall** (card-clip; the case mount's duct uses 80 mm). It blows
  along the card length, the direction server NIC heatsink fins are designed for. Use a high-static-pressure fan.
- **Optional booster: 120 mm low-profile (slim, ~15 mm) fan** (`booster: none | side_cover_120`).
  With a booster, the tail duct and side cover join into **one plenum around the slot area**. The joint between
  them is sealed so the two fans don't fight, but the plenum is open at the bracket end (see "Exhaust gap").
  - **`side_cover_120`** (the only booster option): a printed cover over the cards' top edges holds the slim fan
    inside the case, blowing toward the motherboard. The fan's intake faces the steel side panel and its damping
    foam, so it needs at least 15 mm of open space in front of it (`side_clearance` check). If it doesn't fit,
    build without a booster.
  - Don't cut the steel side panel. That would defeat the Silent case's sound damping.
  - Slim fans have low static pressure. The 80 mm fan stays the primary; the booster adds volume, mainly for the
    hot NIC chips and the SFP+/QSFP cages near the brackets.
  - The plenum's top wall still has to respect `gpu_clearance_min` so the GPU can draw intake air.
- A 120 mm fan at the card tails, in place of the 80 mm, only fits if `slot_positions_covered × 20.32` plus
  the clearances is at least 120 mm. Check this after measuring; otherwise keep the 80 mm.

## Toolchain
- Python 3.11+ with **build123d** (OpenCascade B-rep CAD, parametric, exports STEP and STL)
- `trimesh` for mesh validation in tests
- `pytest` for tests
- Optional: `ocp_vscode` for live viewing while iterating
- All dimensions in millimetres

Setup: the devcontainer builds the whole environment, with pinned Python packages in `requirements.txt`.
Read `AGENTS.md` before changing or debugging the environment.

@AGENTS.md

## Repo layout
```
duct/
  params.py        # dataclass of every dimension, loaded from a TOML config
  fan.py           # 80 mm fan flange + hole pattern
  transition.py    # loft from fan opening to card-stack outlet
  outlet.py        # outlet flange, gasket lip, per-slot splitter vanes
  plugs.py         # snap-in blanking plugs for empty slot channels
  tray.py          # floor tray sealing the card-zone perforations; also the mount
  booster.py       # optional 120 mm slim-fan side cover joining the tail duct into a plenum
  mounts.py        # case mount (default) and optional card-end clips
  coupons.py       # fit-test prints exported with --coupons
  export.py        # STL/STEP export and per-body print-oriented STLs
  build.py         # assembles parts, exports to out/
  slice.py         # headless ElegooSlicer: writes the project 3MFs and slices them
configs/
  default.toml     # this machine's measurements
  slicer_overrides.json  # process settings applied on top of the vendor profile (rigid parts)
  slicer_overrides_tpu.json  # the same for TPU parts
  filament_tpu72d.json   # TPU 72D preset derived from the vendor TPU 95A profile
tests/
  test_geometry.py
out/               # generated STL/STEP/3MF and sliced gcode (gitignored)
print/             # print-ready 3MF per part plus PRINTING.md, refreshed by --print-dir
```

Build command: `python -m duct.build --config configs/default.toml`

## Fixed reference dimensions
| Item | Value |
|---|---|
| 80 mm fan frame | 80 × 80 mm, 25 mm deep (param, 15/25/38 options) |
| Fan hole spacing | 71.5 mm centre-to-centre, 4.3 mm holes (M4 / fan screws) |
| 120 mm fan | 120 × 120 mm, 105 mm hole spacing, 15 mm (slim) or 25 mm deep |
| PCIe slot pitch | 20.32 mm |
| Low-profile PCB height | 68.9 mm |
| Full-height card bracket height | 120 mm (PCB height 111.15 mm) |

## Parameters to measure (fill in configs/default.toml)
- `slot_positions_covered`: the number of slot positions below the GPU's footprint, down to the bottom-most slot
- The position of the bottom-most slot relative to the PSU shroud
- `gpu_clearance`: the gap from the bottom of the GPU's fans or shroud to the top slot position the duct covers
- `outlet_offset_from_bracket` and the free length from there toward the front of the case, including cables and drive cages
- The motherboard surface height relative to the case (the card zone starts at the PCB surface plus the slot connector)
- PSU shroud height under the bottom slot
- `side_clearance`: the gap from the top edge of a full-height card bracket to the damping foam on the steel side panel
- `midplate_gap`: the height from the bottom slot position to the top of the midplate (limits the duct's bottom wall and mount foot)
- Midplate perforations: hole shape and diameter, pitch, pattern (square or hex grid), sheet thickness, and the
  perforated area's extent relative to the card brackets
- `under_midplate_gap`: confirm the ~15 mm gap between the midplate and the PSU

## Design rules
**Airflow**
- The outlet covers every slot position below the GPU, at full card-zone height (see "Core requirement").
- Use equal-width channels, one per slot position, divided by splitter vanes at the 20.32 mm slot boundaries.
  Vanes run the full duct length so the airflow split doesn't depend on which slots are populated.
- Blanking plugs fit any channel, friction-fit or with a snap tab, and print flat without supports.
- The 80 mm fan's intake must draw the coolest air available (toward the front of the case). It must not draw from the GPU's warm exhaust zone.
- The duct's top surface must leave at least `gpu_clearance_min` (default 10 mm) below the GPU's fans so the GPU can still draw intake air.
- Add a 2–3 mm outlet lip to take a foam or TPU gasket for sealing against the heatsinks.
- **Exhaust gap:** some of the network cards have solid brackets with no vents, so the air can't be forced out
  through the back of the case. Nothing the duct adds may enclose the last `exhaust_gap` (default 20 mm) of the
  slot area before the brackets. Air reaching the bracket end must be able to escape sideways toward the side panel and
  up toward the top exhaust fans. In practice:
  - The tail duct already ends at the card tails, so the bracket end is open in the 80 mm-only build.
  - The booster's side cover stops `exhaust_gap` short of the brackets, and its edge there is rounded or chamfered
    so air turns out smoothly.
  - Vented slot covers and bracket vents are a bonus if present, never a requirement.
- Recommend a high-static-pressure 80 mm fan in the README (rated mmH2O matters more than CFM).

**Fan control notes for the README**
- Supermicro IPMI uses lower-critical RPM thresholds. Slow, quiet fans can trip them, which makes the BMC
  cycle all fans to full speed. Document lowering the thresholds with `ipmitool sensor thresh`.
- Supermicro boards control fans by zone. Note which header zone the duct fan should use.

**Printer and output files**
- Printer: **Elegoo Centauri Carbon 2 Combo** (FDM, 256 × 256 × 256 mm bed, 0.4 mm hardened nozzle, enclosed
  passive chamber, CANVAS 4-spool changer, which feeds TPU too). Filaments on hand: PLA, ABS, TPU 95A and
  Elegoo TPU 72D (Shore D, harder than 95A). Use ABS for rigid parts and TPU 95A for the gasket and the grips.
  ElegooSlicer 1.5.3.5 runs headless in the devcontainer as `elegooslicer`; `python -m duct.slice` slices every
  exported part with the Centauri Carbon 2 profiles plus `configs/slicer_overrides.json`.
- Deliverables: one **3MF** per part, already rotated into its print orientation and placed on the bed, written by
  ElegooSlicer's own CLI (`duct/slice.py`) from the oriented STLs so it is a real project file with the printer,
  process and filament presets embedded; two-material parts are one object with per-part filaments. A bare mesh 3MF
  (build123d `Mesher`, lib3mf) makes ElegooSlicer warn and load geometry only, so never ship those. Also export STL for
  each part and a STEP of the full assembly for later edits.
- Write `out/PRINTING.md` (copied to `print/`) listing each part, its quantity, orientation, material, and suggested slicer settings.
- If the printer is resin: use a tough or high-temperature resin (standard resin is brittle and softens near hot
  parts), hollow nothing, keep walls ≥ 2 mm, and fit parts within the build plate.

**Printability**
- Print without supports in at least one orientation. Prefer printing with the outlet face down.
- Wall thickness 2.0 mm by default (minimum 1.6 mm, i.e. 4 perimeters at 0.4 mm).
- If any part exceeds the bed size, split it with alignment pins and screw bosses.
- Target material is ABS (PETG and ASA are not on hand). The 7900 XT exhaust makes PLA a poor choice.
- Use heat-set insert bosses (M3) instead of printed threads where a part needs a threaded hole. Fan screws thread into the fan frame, as fans expect, never into the print.

**Mounting** (selectable via `mount_style`; `card_clip` is the current default because the midplate has a
cable cutout and slot perforations where the tray and fan were going to sit)
1. `case`: the **floor tray is the mount**. The duct bolts to the tray, and the tray anchors into the
   card-zone perforations (which it covers anyway) with printed pegs or a twist-lock, so no drilling or adhesive is
   needed. Pegs are sized to the measured hole diameter and pitch with `peg_clearance` (default 0.2 mm). The tray is
   thin (`tray_thickness`, default 1.6 mm) to fit under the bottom card within `midplate_gap`, and it lifts out
   in one piece when cards are swapped.
   The duct must stay put when cards are swapped, so it can't depend on any particular card.
2. `card_clip` (default): an ABS side wall with one dovetail groove per card plus a bottom plate. A TPU 95A
   U-channel grip per card, with a dovetail key on its back, slides into its groove from the shroud's open
   bracket end; the shroud then goes on from the side panel and the grips push onto the cards' top PCB
   edges (2.5 mm down both faces). No screws hold the grips. The top card's PCB is the
   roof of the top channel, so there is no lid under the GPU. The tail end wall carries the 60 mm fan (`[tail]`
   in the config). At the bracket end one rib per card runs along the wall's outer face to its edge and angles up to an
   ear under that card's PCI bracket screw, so the bracket screws hold cards and shroud (`[bracket]`, positions
   still to measure). A ridge along each long edge of the rib stiffens it up to the screw head
   (`bracket_screw_head_clearance`). The ribs keep
   the exhaust gap open between them. The shroud prints standing on its tail wall. Nothing touches the midplate.
   The `case` mount and its separate 80 mm duct remain in the code but do not fit this machine.
3. Always include zip-tie slots as a fallback.

## Tests (tests/test_geometry.py)
- Each exported STL is watertight and has positive volume.
- The outlet spans `slot_positions_covered × 20.32 mm` and `card_zone_height` within ±0.2 mm.
- There is one channel per slot position, with vanes on the 20.32 mm grid.
- No part of the duct is closer to the bracket than `outlet_offset_from_bracket`.
- With a booster, no part of the side cover is within `exhaust_gap` of the brackets.
- Mount pegs match the configured perforation pitch and diameter.
- The floor tray covers the card zone from the duct outlet plane to `exhaust_gap` before the brackets, and leaves the intake and exhaust zones uncovered.
- The tray plus its pegs' heads fit within `midplate_gap` below the bottom slot position.
- Fan hole spacing is 50 mm on the card-clip tail wall (71.5 mm on the case-mount duct).
- Minimum wall thickness is at or above the configured value.
- The duct envelope stays below the `gpu_clearance` plane.
- With a booster, every plenum joint is closed (no gaps above 0.5 mm), and the side cover plus its fan intake gap fits within `side_clearance`.
- Every part fits the configured printer bed (or is split).

## Milestones
1. `params.py` + config loading + fan flange; test-print the flange to check fan fit.
   Also test-print a small peg coupon to check the fit in the midplate perforations.
2. Transition from the 80 mm fan to the full slot-span outlet; test-fit a coupon in the case.
3. Per-slot splitter vanes, blanking plugs, gasket lip and GPU-clearance check.
3b. Floor tray: card-zone coverage, peg pattern, gasket joint to the duct; split into bed-sized pieces if needed.
4. Mount styles, part splitting and bed-fit checks.
4b. Optional side-cover booster: 120 mm hole pattern (105 mm spacing), sealed joint to the tail duct, side-clearance check.
5. README with print settings, fan recommendation, IPMI threshold commands and exhaust-gap notes.

## Working conventions for Claude
- Never hard-code a dimension in geometry code. Everything comes from `params.py`.
- After any geometry change, run the build and the tests before reporting done.
- Keep test-print-sized fit coupons (fan corner, outlet corner) exportable via `--coupons`.
- Ask for measurements rather than guessing when a TODO value blocks progress.
