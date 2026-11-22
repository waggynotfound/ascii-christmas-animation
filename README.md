# Its Christmas Eve! 🌲❄️

An animated Christmas scene that runs entirely inside a terminal window, drawn
with ASCII characters and 24-bit colour. No images, no video files, no third
party packages — just Python and a console.

Closest thing to a screenshot: `preview.png`.

<img width="1376" height="775" alt="preview" src="https://github.com/user-attachments/assets/85e98c87-b6be-44fe-9efd-5198b1dba5b3" />

---

## Quick start

1. Install **Python 3** from <https://www.python.org/downloads/> — during setup
   tick **"Add python.exe to PATH"**.
2. Double-click **`run_winter_night.bat`**.

That's it. The launcher opens a 170x46 console, runs the scene, and closes when
you stop it.

### From a terminal instead

```bat
cd /d "D:\codesss\christmas ascii"
python winter_night_ascii.py
```

Press **Ctrl+C** to stop (the cursor and colours are restored on the way out).

---

## The opening sequence

The scene builds itself every time it starts:

| Time | Stage |
|------|-------|
| 0.3 s – 2.4 s | The distant pine forest rises out of the snow, spreading from the middle outwards. Each pine grows in width as well as height. |
| 2.3 s – 4.2 s | The Christmas tree grows from the trunk to the tip. Lights, garland, baubles and the snow on the branches appear only above the growth line, so nothing floats. |
| ~4.1 s | The gold star pops onto the finished tip. |
| 4.55 s – 5.9 s | The four presents spring out of the ground with a small overshoot, land, then settle into their idle animation — only the lid bobs. |
| 6.15 s → | Fireworks start and the scene runs until you stop it. |

Timings live in the constants `T_PINES`, `T_TREE`, `T_TREE_DUR` and `T_GIFTS`
at the top of the `Scene` class if you want to retune the pacing.

---

## What is on screen

Drawn back to front, one character per pixel:

- **Sky** — banded gradient wash, twinkling star field, a small white moon, a
  warm planet, and a large blue planet (all shaded discs, not flat blobs).
- **Forest** — blue pine silhouettes with no decorations, sitting on the
  horizon in front of a haze band.
- **Snow field** — three depth bands of blue glitter, twinkling sparks, drifts
  along the bottom edge, and a trail of footprints walking in from the left.
- **Weather** — falling snow as small `.` and `'` glyphs, plus the occasional
  shooting star.
- **Fireworks** — shells launch only from the lanes either side of the tree.
  Shapes: peony, ring, palm, willow and crackle. Each burst gets an ignition
  flash, a hot core, a glow halo, falling drips, drifting smoke, and an
  afterglow trail so the motion stays smooth instead of blinking.
- **Tree** — solid cone with tier banding, gold and red baubles, a red ribbon
  spiralling down, chasing lights, snow on the branches, and a star topper.
- **Presents** — four striped boxes in front of the trunk with ribbon, bow,
  lit top edge and a shadow; the lids bounce a single line.
- **Light spill** — coloured glow from fireworks reflects on the snow, and the
  tree casts a warm patch under itself.

---

## Options

```
python winter_night_ascii.py [options]
```

| Option | Default | What it does |
|--------|---------|--------------|
| `--seconds N` | `0` (forever) | Play for N seconds, then exit. |
| `--fps N` | `20` | Frames per second. Raise it on a fast PC for smoother fireworks. |
| `--cols N` | window width − 1 | Scene width in characters. More columns = finer detail. |
| `--rows N` | window height − 2 | Scene height in characters. |
| `--once` | off | Print a single frame and exit (good for piping or screenshots). |
| `--time N` | `6.0` | Scene time for `--once`, e.g. `--time 1.5` to see the intro. |
| `--seed N` | `5` | Changes the layout: stars, tree shape, presents, fireworks order. |
| `--no-truecolor` | off | Fall back to 256-colour codes on consoles without 24-bit support. |

Examples:

```bat
python winter_night_ascii.py --seconds 10
python winter_night_ascii.py --cols 200 --rows 50 --fps 24
python winter_night_ascii.py --once --time 1.2
python winter_night_ascii.py --seed 12
```

The scene sizes itself to the window, so **maximise the console before
starting** for the most detail.

---

## Files

| File | Purpose |
|------|---------|
| `winter_night_ascii.py` | The scene. Single file, standard library only. |
| `run_winter_night.bat` | Windows launcher: sets the window size, finds Python, runs the scene, pauses at the end. |
| `preview.png` | A still of the finished scene. |

---

## Requirements

- Windows 10 or newer (tested on Windows 10 Pro 22H2, Python 3.15).
- Any terminal with ANSI support. Modern cmd.exe, Windows Terminal, PowerShell,
  macOS Terminal and most Linux terminals all work.
- No `pip install` needed. Nothing is written to disk while it runs.

The script turns on UTF-8 (`chcp 65001`) and virtual-terminal processing by
itself on Windows, so escape codes are interpreted rather than printed.

---

## Troubleshooting

**The screen shakes or scrolls.**
The grid is deliberately one column and one row smaller than the window, with
no trailing newline, so it cannot wrap. If it still scrolls, the console font
is probably too large for the chosen size — run with a smaller scene, e.g.
`--cols 140 --rows 34`, or lower the font size with Ctrl+scroll.

**Colours look wrong / everything is green or dull.**
Your console is approximating the palette. Try Windows Terminal, or run with
`--no-truecolor`. Colour 24-bit output needs Windows 10 build 1703 or later.

**Characters appear as boxes or question marks.**
The console font lacks the glyphs. Switch to Consolas or Cascadia Mono in the
console properties.

**`python` opens the Microsoft Store.**
Python is not actually installed. Reinstall from python.org with "Add
python.exe to PATH" ticked, or use the `py` launcher:
`py winter_night_ascii.py`.

**It runs too slowly.**
Drop `--fps 15`, or reduce `--cols` / `--rows`. Full-screen consoles redraw a
lot of characters per frame.

---

## Notes on how it works

- The picture is a list of 256-colour palette indices, one per cell. Each frame
  copies the static background, overlays the animated layers, then converts
  every cell to a glyph by mapping its perceived brightness onto a ramp
  (`" .`'^",:;-~+=ilrczxo*#%@"`). A few layers (snow, sparks) force their own
  glyph so they read as dots rather than bright blobs.
- Fireworks use a separate `energy` buffer that decays every frame
  (`decay = dt * 1.15`). Drawing into it rather than straight to the grid is
  what produces the glow and the trailing afterimage.
- Colour is emitted as `ESC[38;2;r;g;bm` (24-bit) because cmd.exe only has 16
  base colours and maps 256-colour codes onto them badly.
- Everything is stdlib: `math`, `random`, `os`, `sys`, `time`, `shutil`,
  `argparse`, and `ctypes` on Windows to enable ANSI mode.

Set the console background to black and use a monospace font for the intended
look.
