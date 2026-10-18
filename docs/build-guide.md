# Corne LP build guide

Everything you need to go from a pile of parts to a working keyboard. Expect a weekend: about a day of printing and an evening of soldering.

[← back to the README](../README.md)

1. [Parts](#1-parts)
2. [Print](#2-print)
3. [Flash first](#3-flash-first-before-anything-is-closed-up)
4. [Wire it](#4-wire-it)
5. [Assemble](#5-assemble)
6. [Firmware: edit and rebuild](#6-firmware-edit-and-rebuild)
7. [Change the design](#7-change-the-design)
8. [Things to know](#8-things-to-know)

---

## 1. Parts

For both halves:

| Qty | Part | Notes |
|---|---|---|
| 2 | SuperMini nRF52840 | nice!nano-compatible |
| 42 (+3 spare) | Gateron KS-33 Low Profile 2.0 switches | |
| 42 | **CLP keycaps**, 3D-printed (vvhg1/clp-keycaps, GPL v3), KS-33 version | 10 Saddle, 2 Saddle Homing, 24 Tilt 7, 4 Thumb, 2 Tilt 7 1.5u. Files in [`print/keycaps/`](../print/keycaps) |
| 45 | 1N4148 diodes | through-hole |
| 2 | 0.91″ OLED, SSD1306, 128×32, I²C (Robu, white) | 4 pins in this order: GND, VCC, SCL, SDA. PCB 38 × 12 × 1.2 mm, glass 30 × 11.5 mm. If it comes with header pins soldered on, remove them and solder wires straight to the pads |
| 2 | 3.7 V LiPo **WLY450838** (4.5 × 8 × 38 mm, 120 mAh, protected), Robu, ₹109 | The pocket allows **39.3 mm** including the protection board on the end: check yours before printing |
| 2 | XKB SS-12D06L4 slide switch (Robu) | lies on its side; the knob sticks out ~2 mm through the inner side wall |
| 1 | Cirque **TM023023-2024-002** | the -2024 version is the SPI one |
| 2 | 3 × 6 × 2.5 mm 2-pin tactile switch (SMD or bent-leg) | rescue reset, one per half, pressed with a paperclip through the base |
| 8 | 6 × 1 mm N52 neodymium disc magnets | glued flush into the 1 mm base |
| 14 | M2 × 4 mm brass heat-set inserts | e.g. Robu "M2 X 4 mm Brass Insert" (10-pack, so get 2 packs) |
| 14 | **M2 × 5 mm** countersunk machine screws (DIN 965 / ISO 7046) | 7 per half. Buy a pack of 20–25 for spares. M2 × 6 is too long |
| 10 | 8 × 1 mm self-adhesive silicone feet | 5 per half; must be **1 mm or thinner** for bag mode |
| — | 30 AWG silicone wire, solder, flux, Kapton tape, thin double-sided tape, CA glue or 5-min epoxy | the case leaves 5.5 mm under the plate for switches, diodes and wire |
| 1 kg spool | PETG (or PLA for the keyboard, PETG for the carry case) + PLA for keycaps | keyboard ~75 g, carry case ~80 g or bumper ~65 g, keycaps ~25 g, test kit ~6 g |

Where to look in India:
- **Electronics:** Robu.in, Robocraze, ThinkRobotics.
- **Switches and keycaps:** Meckeys, StacksKB.
- **Cirque pad:** Mouser India or element14 India.

---

## 2. Print

Everything printable is in [`print/`](../print):

| Folder | What | Notes |
|---|---|---|
| [`print/test-kit/`](../print/test-kit) | `test_kit.3mf` (+ the three STLs) | **print this first** · ~25 min, 6 g |
| [`print/keyboard/`](../print/keyboard) | `shell_left/right.stl`, `bottom_left/right.stl` | plate side down, no supports |
| [`print/keycaps/`](../print/keycaps) | `Corne-LP_CLP-keycaps_42pcs.3mf` | all 42 caps laid out for OrcaSlicer |
| [`print/carry-case/`](../print/carry-case) | `carry_tray/lid.stl` or `bumper_bottom/top.stl` | pick one: full shell or open bumper |

### Test kit first

**`print/test-kit/test_kit.3mf`** has three pieces:

- **Coupon:** magnet holes 6.0 / 6.2 / 6.4 mm and insert bosses with 2.8 / 3.0 / 3.2 mm holes (1–3 notches each), plus the reset-button cradle and pinhole exactly as in the base. Use the magnet hole a magnet presses into snugly and the insert hole that takes your insert straight. If they're not the middle ones, set `MAG_D` / `INSERT_HOLE` in `case/case.py` and re-run it.
- **CLP Saddle keycap (KS-33 version):** check it pushes onto a KS-33 stem firmly without cracking, and that a full press bottoms out the switch without the cap touching the housing, before you print 42.
- **Switch strip** (`1_switch_strip.stl`): 4 holes marked with 1–4 notches: 13.8, 13.9, 14.0 and 14.1 mm.
  - Use the hole your switch clicks into firmly.
  - **Check the depth too.** The strip has a rim exactly as deep as the case is inside. Click a switch in, solder a scrap wire to a pin the way you'll wire it, trim the pins, and stand the piece on the table: if nothing touches the table, it fits the case.
  - If the hole that fits isn't 14.0, set `HOLE` at the top of `case/case.py` and re-run it (see [Change the design](#7-change-the-design)).

### Keyboard

1. **`shell_left.stl` / `shell_right.stl`**: print as exported, plate side on the bed.
   - Settings: 0.2 mm layers, 3 walls, 20–25 % infill, **no supports**.
   - The top edge chamfer and the OLED bezel come out on the bed side, so they print crisp.
2. **`bottom_left.stl` / `bottom_right.stl`**: flat side down, no supports.

**Set the brass inserts** before anything else goes in the shell:
- **Measure first.** Measure your insert's outside diameter. The holes are 3.0 mm, which suits inserts about 3.2 mm across. If yours are bigger (some are 3.5), set `INSERT_HOLE` in `case/case.py` to *outside diameter − 0.2* and re-run it.
- **Heat-set them.** With the shell upside down, rest an insert on its hole and press it in with a soldering iron at ~220 °C (PLA) or ~250 °C (PETG). Push until it sits about 0.3 mm below the surface; the screw head's tip needs that gap.
- **Let them cool** before you thread anything.

The right shell has the trackpad pocket. The left shell is solid in the same spot, so the two halves keep the same shape for stacking.

<p align="center"><img src="images/diagrams/top_view.png" width="760" alt="Left half seen through the plate: switch grid, screw bosses, magnets, SuperMini, OLED window, battery and power switch"></p>

### Keycaps

**Why not the stock CLP files:** CLP is made for full-height MX switches. Checked against the KS-33 STEP model, a stock cap sits 2.45 mm over the plate and its shell hits the KS-33's wide top housing after only **1.3 mm** of the switch's 3.2 mm travel, before the 1.7 mm actuation point, so most presses wouldn't register. The print files here are the same caps with the round stem made **2.1 mm longer** (it pokes 1.55 mm below the skirt edge). Each cap then rides 2.1 mm higher and gets the full 3.2 mm of travel with 0.2 mm to spare.

- **Easiest:** open `print/keycaps/Corne-LP_CLP-keycaps_42pcs.3mf` in OrcaSlicer. All 42 caps are already standing on a side edge at 70° and laid out (131 × 142 mm). Add supports (they go under the open underside), slice.
- **One file per cap:** `python3 case/clp.py` writes them to `print/keycaps/all-42-caps/` if you'd rather set them up yourself.
- **Fit:** top row Tilt 7 as printed (low edge toward you), bottom row the same cap turned 180°, Saddle on the home row with the homing ones on F / J, Thumb on the two inner thumb keys, Tilt 7 1.5u on the big thumb key.
- **Settings:** 0.2 mm nozzle if you have it, lowest layer height you can stand, no supports inside the stem.

### Carry case (`carry_tray.stl`, `carry_lid.stl`)

A tray and a lid that click shut around the stacked halves. Closed, it's 165 × 107 × **41.7 mm**, about 80 g (it's built around the CLP keycaps; the tallest, the 1.5u thumb, stands 12.85 mm over the plate).

- **Key windows:** every keycap sits in its own window in the lid and the tray, so the keys stay on show. The face stands 0.3 mm proud of the keycap tops, so a laptop or book in your bag rests on the case and never presses a key.
- **Fit:** the lid's rim meets the tray exactly at the seam between the two bases. A 1 mm lip rises 3 mm out of the tray, and 8 short bumps on it click into pockets inside the lid.
- **Blip windows:** both faces have a window over that side's OLED. There's a pocket inside each for an optional clear pane: cut it from 0.5 mm acrylic or print it 0.6 mm thick in clear PETG, about 13 × 31 mm, and glue it in from inside. Blip only shows while the screen is awake; it turns off 30 s after the last key.
- **Looks:** a cursive *Corne* in the thumb lobe (read the right way from both sides), ripple lines flowing round the windows, and grip ribs round the sides.
- **Strap ear:** a tab on the outer end of the tray, flush with its bottom, with a 3 × 10 mm slot for a wrist strap or lanyard.
- **Opening it:** a fingernail notch on the tray's front edge, just under the lid, lets you pop the lid off.
- **Print:** the tray floor-down, the lid face-down (the STL is already flipped). No supports, 3 walls.
- **Material:** **PETG** if you can. PLA snaps work, but they wear out and can crack.
- **Tuning the click:** `BUMP_P` in `case/carry.py` (0.40 mm) sets it. Use 0.30 if it's too stiff, 0.50 if it's loose.
- **Check first:** keycap heights come from the KS-33 STEP model (cap stem resting on the floor of the well round the switch's cross). With the test Saddle pushed fully onto a switch, its top should be about **10.1 mm** above the plate. If yours differs, change `WELL_FLOOR` in `case/clp.py` by the difference and re-run `clp.py` + `carry.py`.

### Bumper case (`bumper_bottom.stl`, `bumper_top.stl`): thinner, keys on show

Two open frames instead of a closed shell. Closed, it's 165 × 107 × **41.7 mm**, about 65 g.

- **How it holds:** each frame has a 1.2 mm flange that rests on the edge of a half's plate, at least 2.2 mm clear of every keycap. The frames click together at the seam with the same lip and bumps as the full case.
- **Protection:** the rim stands 0.3 mm above the keycap tops, so a laptop or book lying on it can't press a key. The keys, both OLEDs and the trackpad stay in view.
- **Also has:** the strap ear, fingernail notch and grip ribs.
- **Print:** the bottom frame ear-side down, the top frame rim-down (the STL is already flipped). No supports.
- **Material and click:** same as the full case (PETG, `BUMP_P`).

---

## 3. Flash first (before anything is closed up)

- Plug in a SuperMini.
- Short **RST to GND twice quickly** (or double-press the reset button once it's wired). A USB drive called `NICENANO` appears.
- Drag [`firmware/corne_lp_left-nice_nano_v2.uf2`](../firmware) onto one board and `corne_lp_right-…uf2` onto the other.
- Mark which board is which.

Later updates don't need the case opened. Hold **NUM + SYM** to reach the ADJ layer, press the **bootloader** key on that half, then drag the new file across.
If a bad firmware ever leaves a half dead, **double-press the reset button** with a paperclip through the pinhole in the base: the `NICENANO` drive appears and you can flash again.

---

## 4. Wire it

Print [`docs/wiring_guide.pdf`](wiring_guide.pdf): the matrix, both halves and the SuperMini pinout, one per page. The pins match a stock Corne, so any Corne diagram agrees with this one.

<p align="center">
  <img src="images/diagrams/wiring_matrix.png" width="49%" alt="Key matrix schematic">
  <img src="images/diagrams/supermini_pinout.png" width="49%" alt="SuperMini pinout with every pad named">
</p>

Most SuperMini boards print the chip's port numbers on the silkscreen (`022`, `111`, …), not D-numbers. Both are given:

| Signal | SuperMini pin | Printed on the board |
|---|---|---|
| Rows R0, R1, R2, R3 | D4, D5, D6, D7 | 022, 024, 100, 011 |
| Columns C0 (outer pinky) → C5 (inner) | D21, D20, D19, D18, D15, D14 | 031, 029, 002, 115, 113, 111 |
| Thumb keys | row R3, sharing columns C3, C4, C5 | |
| OLED SDA / SCL | D2 / D3 | 017 / 020 |
| OLED VCC / GND | 3V3 (VCC) / GND | VCC / GND |
| Battery + | → slide switch (middle pin in, one outer pin out) → **B+** pad | |
| Battery – | **B–** pad | |
| Reset button | one leg → **RST**, the other → **GND** | |

**See it in 3D first.** The viewer's **Wiring** button shows every wire and diode in place, from underneath with the base off (hover a wire for its name). The routes come from `case/routing.py`, which checks them against the switch posts and pins, screw bosses, battery, power switch, reset button, SuperMini and OLED (`python3 routing.py`).

<p align="center"><img src="images/renders/wiring.jpg" alt="Both halves from underneath with the base off: every row and column wire, diode, the SuperMini and the battery"></p>

- Mount every switch with its **two pins toward you** (the edge nearest the thumb keys).
- Column wires run along the switch bottoms past the pin on the left of each switch; rows run just past the diodes, between the rows.
- Runs to the far side of the SuperMini slide **under its USB end** (the rails stop 9 mm short of it); wires from the OLED, reset button, power switch and trackpad cross **over its other end**, under the OLED.

**Diodes.** Solder one leg to a switch pin, and put the **black band toward the row wire**.

**Columns.** A 30 AWG silicone wire connects the other pin of each switch in a column. Keep wires flat and route them between the switches, not over the battery.

<p align="center">
  <img src="images/diagrams/wiring_left.png" width="49%" alt="Left half wiring, seen from underneath">
  <img src="images/diagrams/wiring_right.png" width="49%" alt="Right half wiring with the trackpad, seen from underneath">
</p>

**Trackpad (right half only).**
- Solder 7 short wires (30 AWG silicone, ~6 cm) straight to the pad's back. It runs in SPI mode as it comes (the -2024 version), so don't remove anything on it.

  | Pad pin | Signal | SuperMini |
  |---|---|---|
  | 1 | SCK | D8 (`104`) |
  | 2 | MISO | D0 (`008`) |
  | 3 | SS | D1 (`006`) |
  | 4 | DR | D16 (`010`) |
  | 5 | MOSI | D9 (`106`) |
  | 11 | GND | GND |
  | 12 | VDD | **3V3**. Never connect this to B+ |

- **Find the right spots with a multimeter.** Pins 1–12 are the contacts of the pad's ribbon connector. Solder to the test pads that beep through to those contacts, or carefully to the connector's own legs.
- **Route the wires sideways,** off the edge of the pad toward the SuperMini, not down onto the battery: there's only ~1.8 mm between the battery and the pad's back. Flatten the joints and put Kapton tape over them.

**Test before closing.** Power on and press every key. Watch Blip, and check that keys type on your computer.

---

## 5. Assemble

The battery sits under the thumb lobe, clear of the SuperMini and the OLED:

<p align="center"><img src="images/diagrams/section.png" width="760" alt="Cross-section through the electronics bay"></p>

1. Wire the battery to the board's **B+ / B–** pads first (they're on the underside).
2. Lay the **SuperMini** components-up on its two little rails, USB-C pushed into the back slot. The rails leave room for those battery wires underneath. A strip of thin tape on each rail holds it.
3. Put **Kapton tape** on the battery and lay it in its 0.5 mm dip in the base, under the thumb lobe, protection-board end toward the SuperMini. A strip of double-sided tape holds it.
4. Set the **OLED glass up** against the inside of the window, with the 4-pin end toward the thumbs. It sits 0.6 mm above the SuperMini. Hold it with two strips of tape across the back of its board.
5. Lay the **reset button** face-down (button toward the base) between the two little walls next to the SuperMini, over the pinhole. Solder its legs to RST and GND (bend them flat first). A dab of glue on the walls holds it. Poke the pinhole: you should feel a click.
6. Lay the **slide switch** on its side in its cradle on the base, body against the inner side wall. When the base goes on, the knob slides into the slot in the wall and sticks out about 2 mm. A small **bar** above the slot marks ON: wire the outer pin so that sliding the knob toward the bar turns it on. Bend the 3 pins flat if needed.
7. Drop the **trackpad** (right half) into its pocket from the top. The battery sits right under it. Lay its 7 wires flat along the bay floor to the SuperMini, beside the battery, not on top of it.
8. Close the case with the 7 M2 countersunk screws. Snug is enough; don't crank them into the inserts.
9. **Feet.** Each base has 10 shallow pockets. Stick feet in the 5 pockets marked for that half and leave the other 5 empty. When the halves stack for your bag, every foot drops into an empty pocket on the other half, so the bases sit flat and the magnets touch.

<p align="center"><img src="images/diagrams/bases_underneath.png" width="760" alt="Both bases from underneath: magnets, feet pockets for each half and the reset pinhole"></p>

**Magnets: glue the left base first.**
1. Glue all 4 magnets into the left base's holes, flush with the bottom face. Let them cure.
2. Snap 4 loose magnets onto those, so they settle the right way round.
3. Put glue in the right base pockets.
4. Press the right base, **bottom face down**, onto the loose magnets, lined up with the outline, so they end up flush. Let it cure.

This gets every polarity right.

---

## 6. Firmware: edit and rebuild

[`zmk-config/`](../zmk-config) is a ready-to-push GitHub repo.

1. Create a repo and push the folder.
2. Open **Actions**. Each push builds `corne_lp_left`, `corne_lp_right` and `settings_reset`.
3. Download the zip from the run's Artifacts.

What to change, and where:
- **Keys:** `config/corne_lp.keymap`. Layer names show on the left OLED, so keep them to 5 letters.
- **Blip is upside down:** uncomment `CONFIG_CORNE_LP_OLED_FLIP=y` in `config/corne_lp.conf`.
- **Trackpad axes feel swapped or reversed:** edit `rotate-90` / `x-invert` / `y-invert` in `boards/shields/corne_lp/corne_lp_right.overlay`.
- **Blip's art:** edit `tools/sprites.py` and run it.
- **Preview the screen on a PC:**
  ```
  cc -Isrc tools/sim.c src/ui_core.c -o sim && ./sim > f.bin && python3 tools/preview.py f.bin preview.gif
  ```

**Layers:**

| Layer | What's on it |
|---|---|
| BASE | QWERTY |
| NUM | numbers, arrows, media, and trackpad clicks (F = left, D = middle, S = right) |
| SYM | symbols, Caps Word |
| ADJ | BT profiles 1–5, BT clear, bootloader on both halves, reset, soft-off |

Taps on the trackpad also click.

---

## 7. Change the design

The whole case is generated by Python in [`case/`](../case). Every dimension that depends on your parts is a parameter at the top of `case/case.py`. Edit it and re-run:

```
pip install -r case/requirements.txt cadquery-ocp
cd case
python3 case.py          # quick STLs -> print/keyboard/ (+ the switch strip in print/test-kit/)
python3 step.py          # STEP solids -> cad/, viewer meshes, and the final printable STLs (meshed from the solids)
python3 clp.py           # keycap heights, keycap print package -> print/keycaps/, viewer keycap meshes
python3 carry.py         # carry case + bumper -> print/carry-case/ + cad/ + viewer meshes (needs clp.py's heights)
python3 testkit.py       # test-print kit -> print/test-kit/
python3 routing.py       # wire routes + diodes (viewer Wiring view), clearance report
python3 ks33_check.py    # every keycap vs the KS-33 model (ref/ks33.step): free travel must be >= 3.2 mm
python3 preview.py       # drawings -> docs/images/diagrams/
python3 wiring.py        # wiring diagrams + docs/wiring_guide.pdf
python3 bottoms.py       # base underside drawing
python3 viewer_data.py   # viewer layout data
python3 ../viewer/build.py   # bundles viewer/dist/index.html
```

Only `case.py`, `preview.py`, `wiring.py`, `bottoms.py` and `testkit.py` work without `cadquery-ocp`; the rest build true B-rep solids with OpenCascade.

- `case/styles.py` draws the other case shapes that were considered ([`docs/images/style-options/`](images/style-options)).
- `case/keycaps.py` is an older generator for flat caps (the build uses CLP).
- **README renders:** [`tools/render/`](../tools/render) drives the 3D viewer in headless Chromium (`npm install && node render.mjs && python3 compose.py`).

**Big files:** the carry-case and bumper STEP files (25–58 MB each) are zipped in `cad/carry_bumper_step.zip`. `print/keycaps/all-42-caps/` (one file per cap) and `cad/assembly_both_halves.step` are not committed: `python3 case/clp.py` and `python3 case/step.py` rebuild them. `case/ks33_check.py` needs a Gateron KS-33 STEP model at `ref/ks33.step` (not included: third-party model).

---

## 8. Things to know

- **Battery life.** The OLEDs are the biggest drain.
  - Screens turn off after 30 s idle. The boards deep-sleep after 15 minutes, and any key wakes them.
  - The trackpad drops to about 40 µA once your finger has been off it for 5 s.
  - The right half transmits at 0 dBm (it only talks to the left half) and the left at +8 dBm (to your computer). If the halves drop out, set the right to `CONFIG_BT_CTLR_TX_PWR_PLUS_4=y` in `zmk-config/config/corne_lp_right.conf`.
  - Expect about 4 days of normal use per charge on the 120 mAh cells (an estimate, not measured). The right half drains faster because of the pad.
- **WPM on the right half.** The right half only sees its own keys, so its WPM is an estimate (doubled). The left half's number is exact.
- **Bluetooth range.** The SuperMini's antenna sits under the OLED. If range is poor, test with the shell off. Most desks are fine.
- **Measured guesses.** A few dimensions were taken from spec sheets and typical modules rather than parts in hand. All of them are parameters at the top of `case/case.py`:
  - KS-33 depth below the plate (check it with the fit-test strip)
  - OLED module size
  - USB-C height (the plate has a pocket over it)
  - Battery size

  Check your parts against the cross-section above before printing everything.
