# Corne LP: case print order

A handwired wireless split keyboard. Four parts: a shell and a base for each half.
All files are watertight single-shell STLs in **millimetres. Please don't scale them.**
Source: https://github.com/FBIopeningUPP/corne-lp-handwired

| File | Qty | Size mm (X × Y × Z) | Volume | Orientation |
|---|---|---|---|---|
| `shell_left.stl` | 1 | 159.0 × 100.8 × 6.7 | 17.2 cm³ | plate side down, as the file sits |
| `shell_right.stl` | 1 | 159.0 × 100.8 × 6.7 | 16.4 cm³ | plate side down (has the trackpad pocket) |
| `bottom_left.stl` | 1 | 159.0 × 100.8 × 2.8 | 10.6 cm³ | flat side down |
| `bottom_right.stl` | 1 | 159.0 × 100.8 × 2.8 | 10.6 cm³ | flat side down |

Total about 55 cm³ (roughly 75 g).

## What to ask for
- FDM, **PLA or PETG** (PETG is tougher), any colour.
- 0.2 mm layers, **3 walls**, 20–25 % infill, **no supports**, no brim or raft.
- Print each part in the orientation the file sits in. The shells print plate side down so the top edge and the OLED window come out crisp.
- Tolerance about ±0.1 mm. The fit-critical features are the switch cut-outs (14.0 mm), the magnet pockets (6.2 mm) and the insert holes (3.0 mm). **Please turn off hole compensation, scaling and sanding.**
- No post-processing needed. Resin and powder (SLS/MJF) prints haven't been tried.

## One thing to know before ordering
Those three hole sizes come from spec sheets and haven't been checked on a printed part yet, and every printer lands a little differently. The repo has a 25-minute, 6 g test kit (`print/test-kit/test_kit.3mf`, or the three STLs next to it) that checks them. If you want to be safe, print that first and tell me which holes fit. I can regenerate the case files to match before you pay for the full set.
