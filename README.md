# Image Picker

A small Python/Tkinter desktop tool for reducing a folder of image candidates
through side-by-side comparisons. A selected winner stays on screen and faces
the next randomly ordered candidate. Intended for local art-review workflows.

## Safety First

**Choosing a winner permanently deletes the other image, not to the recycle
bin.** It also deletes that image's Godot `.import` sidecar, its matching
`<stem>_base<extension>` companion, and the companion's `.import` sidecar.
There is no undo or confirmation per choice. Start with a disposable copy of
your images, not your only originals.

`Pool` moves both displayed images into `_pool/` inside the selected folder,
renaming on collisions. Companion files are not moved with them. `Skip` puts
both images back at the end of the current comparison queue without deleting
them. Opening a folder creates its `_pool/` directory.

## Setup And Start

Use Python 3.10+ with Tkinter and a graphical desktop. Pillow is the only
third-party import in the image picker. No dependency manifest or lockfile is
included; the following is a manual setup, not a pinned environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pillow
.\.venv\Scripts\python.exe image_picker.py "C:\path\to\image-copies"
```

With dependencies already available in your active Python environment:

```powershell
python image_picker.py
python image_picker.py --help
```

Run from this repository's directory. The optional positional folder argument
opens that folder directly. Without it, the app tries the first configured
favorite; use the folder button if no favorite is available. On Windows,
`image_picker.bat` launches with `python` from PATH, not automatically `.venv`.

## Configuration

Edit the existing `image_picker_config.json` to replace machine-specific
favorites with your own folders. Its format is:

```json
{
  "favorites": [
    {"name": "Review copies", "path": "C:/path/to/image-copies"}
  ]
}
```

The script also has machine-specific fallback favorites. Neither these paths
nor an external game project are portable prerequisites: supply your own folder.
The config is currently tracked; ignore rules do not hide changes to it.

## Code Map

| File | Responsibility |
| --- | --- |
| `image_picker.py` | CLI, favorites, Tkinter UI, random comparison queue, deletion and pool operations |
| `image_picker_config.json` | Favorite labels and local folder paths |
| `image_picker.bat` | Windows launcher |

## Limitations And Checks

- Scans only immediate files, not subdirectories. Supports PNG, JPG/JPEG,
  WebP and BMP; `_base` stems are excluded from comparisons.
- Same-stem files with different extensions collapse into one candidate;
  which extension wins is not specified.
- No ratings, persistent review history, undo, or batch export. Finish needs
  at least two candidates for a comparison; repeated Skip can keep cycling.
- Preview rendering uses Pillow; unsupported/corrupt images show an error
  rather than being validated before entering the queue.
- No test suite or CI configuration is included. A non-GUI CLI smoke check is
  `python image_picker.py --help`; it still requires Tkinter and Pillow imports.
