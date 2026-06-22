from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import tkinter as tk
from tkinter import filedialog
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox

try:
    from PIL import Image, ImageTk
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Pillow is required. Install with: python -m pip install pillow"
    ) from exc


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "image_picker_config.json"
DEFAULT_FAVORITES = [
    {
        "name": "Portrait History",
        "path": r"E:\work\new_game\src\test-game\assets\portraits\history",
    },
    {
        "name": "Comfy Output",
        "path": r"C:\Users\nanbu\AppData\Local\Comfy-Desktop\ComfyUI-Shared\output",
    },
]


@dataclass
class Pair:
    left: Path
    right: Path


def list_images(folder: Path) -> list[Path]:
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    chosen: dict[str, Path] = {}
    for path in files:
        stem = path.stem
        base_key = stem[:-5] if stem.endswith("_base") else stem
        if stem.endswith("_base"):
            continue
        chosen[base_key] = path
    result = list(chosen.values())
    result.sort(key=lambda p: p.name.lower())
    return result


def remove_godot_import_files(path: Path) -> None:
    import_file = Path(str(path) + ".import")
    if import_file.exists():
        import_file.unlink()
    if path.suffix.lower() != ".import":
        stem_import = path.with_suffix(path.suffix + ".import")
        if stem_import.exists():
            stem_import.unlink()


def remove_companion_base(path: Path) -> None:
    if path.stem.endswith("_base"):
        return
    base_path = path.with_name(f"{path.stem}_base{path.suffix}")
    if base_path.exists():
        try:
            base_path.unlink()
        except FileNotFoundError:
            pass
        remove_godot_import_files(base_path)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"favorites": DEFAULT_FAVORITES}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"favorites": DEFAULT_FAVORITES}


def save_config(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ImagePickerApp:
    def __init__(self, root: tk.Tk, folder: Path | None):
        self.root = root
        self.folder = folder
        self.config = load_config()
        self.pool_dir: Path | None = None
        self.images: list[Path] = []
        self.queue: list[Path] = []
        self.current_winner: Path | None = None
        self.current_pair: Pair | None = None
        self.left_photo = None
        self.right_photo = None

        self.root.title("Image Picker")
        self.root.geometry("1500x900")
        self.root.configure(bg="#1d1a16")

        self._build_ui()
        if self.folder is not None:
            self._load_folder(self.folder)

    def _build_ui(self) -> None:
        top = tk.Frame(self.root, bg="#1d1a16")
        top.pack(fill="x", padx=10, pady=8)

        choose_button = tk.Button(
            top,
            text="フォルダを選ぶ",
            command=self._choose_folder,
            bg="#5a4a31",
            fg="#fff3d7",
            font=("Meiryo", 12, "bold"),
            width=16,
        )
        choose_button.pack(side="left", padx=(0, 10))

        self._build_favorite_buttons(top)

        self.status_var = tk.StringVar()
        self.status = tk.Label(
            top,
            textvariable=self.status_var,
            fg="#f3e3bf",
            bg="#1d1a16",
            anchor="w",
            font=("Meiryo", 12),
        )
        self.status.pack(side="left", fill="x", expand=True)

        self.pool_label_var = tk.StringVar(value=f"Pool: {self.pool_dir}")
        pool_label = tk.Label(
            top,
            textvariable=self.pool_label_var,
            fg="#b8a47e",
            bg="#1d1a16",
            anchor="e",
            font=("Meiryo", 10),
        )
        pool_label.pack(side="right")

        body = tk.Frame(self.root, bg="#1d1a16")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.left_frame = tk.Frame(body, bg="#2a241d", bd=2, relief="groove")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.right_frame = tk.Frame(body, bg="#2a241d", bd=2, relief="groove")
        self.right_frame.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self.left_name = tk.Label(self.left_frame, text="", bg="#2a241d", fg="#f6e7c8", font=("Meiryo", 11, "bold"))
        self.left_name.pack(fill="x", padx=8, pady=(8, 4))
        self.left_canvas = tk.Canvas(self.left_frame, bg="#1a1612", highlightthickness=0)
        self.left_canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.left_pick = tk.Button(
            self.left_frame,
            text="Choose Left",
            command=lambda: self._choose_side("left"),
            bg="#4d5e43",
            fg="#fff3d7",
            font=("Meiryo", 11, "bold"),
        )
        self.left_pick.pack(fill="x", padx=8, pady=(0, 8))

        self.right_name = tk.Label(self.right_frame, text="", bg="#2a241d", fg="#f6e7c8", font=("Meiryo", 11, "bold"))
        self.right_name.pack(fill="x", padx=8, pady=(8, 4))
        self.right_canvas = tk.Canvas(self.right_frame, bg="#1a1612", highlightthickness=0)
        self.right_canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.right_pick = tk.Button(
            self.right_frame,
            text="Choose Right",
            command=lambda: self._choose_side("right"),
            bg="#4d5e43",
            fg="#fff3d7",
            font=("Meiryo", 11, "bold"),
        )
        self.right_pick.pack(fill="x", padx=8, pady=(0, 8))

        buttons = tk.Frame(self.root, bg="#1d1a16")
        buttons.pack(fill="x", padx=10, pady=(0, 10))

        self.pool_button = tk.Button(
            buttons,
            text="Pool",
            command=self._pool_pair,
            bg="#5a4a31",
            fg="#fff3d7",
            font=("Meiryo", 12, "bold"),
            width=12,
        )
        self.pool_button.pack(side="left")

        self.skip_button = tk.Button(
            buttons,
            text="Skip",
            command=self._skip_pair,
            bg="#3f372c",
            fg="#fff3d7",
            font=("Meiryo", 12),
            width=12,
        )
        self.skip_button.pack(side="left", padx=(8, 0))

        self.quit_button = tk.Button(
            buttons,
            text="Quit",
            command=self.root.destroy,
            bg="#4a2323",
            fg="#fff3d7",
            font=("Meiryo", 12),
            width=12,
        )
        self.quit_button.pack(side="right")

    def _build_favorite_buttons(self, parent: tk.Widget) -> None:
        fav_frame = tk.Frame(parent, bg="#1d1a16")
        fav_frame.pack(side="left", padx=(0, 10))
        favorites = self.config.get("favorites", DEFAULT_FAVORITES)
        for fav in favorites:
            label = fav.get("name", "Favorite")
            button = tk.Button(
                fav_frame,
                text=label,
                command=lambda p=fav.get("path", ""): self._open_favorite(p),
                bg="#3f372c",
                fg="#fff3d7",
                font=("Meiryo", 10),
                width=14,
            )
            button.pack(side="left", padx=(0, 6))

    def _open_favorite(self, raw_path: str) -> None:
        if not raw_path:
            return
        folder = Path(raw_path).expanduser()
        if folder.is_dir():
            self._load_folder(folder)
            return
        messagebox.showwarning("Image Picker", f"Folder not found:\n{folder}")

    def _choose_folder(self) -> None:
        chosen = filedialog.askdirectory(title="画像フォルダを選んでください")
        if chosen:
            self._load_folder(Path(chosen))

    def _load_folder(self, folder: Path) -> None:
        self.folder = folder
        self.pool_dir = folder / "_pool"
        self.pool_dir.mkdir(exist_ok=True)
        self.pool_label_var.set(f"Pool: {self.pool_dir}")

        self.images = list_images(folder)
        random.shuffle(self.images)
        self.queue = self.images[:]
        self.current_winner = None
        self.current_pair = None
        self.pool_button.config(state="normal")
        self.skip_button.config(state="normal")
        self.status_var.set(f"Folder: {folder} | Images: {len(self.images)}")
        self._load_next_pair()

    def _load_next_pair(self) -> None:
        if self.current_winner is not None:
            next_candidate = self._pop_next_image(exclude={self.current_winner})
            if next_candidate is None:
                self._finish()
                return
            self.current_pair = Pair(self.current_winner, next_candidate)
        else:
            left = self._pop_next_image()
            right = self._pop_next_image()
            if left is None or right is None:
                self._finish()
                return
            self.current_pair = Pair(left, right)

        self._render_pair()

    def _pop_next_image(self, exclude: set[Path] | None = None) -> Path | None:
        exclude = exclude or set()
        while self.queue:
            candidate = self.queue.pop(0)
            if candidate in exclude:
                continue
            return candidate
        return None

    def _render_pair(self) -> None:
        assert self.current_pair is not None
        left, right = self.current_pair.left, self.current_pair.right
        self.status_var.set(
            f"Left: {left.name}    |    Right: {right.name}    |    残り: {len(self.queue)}"
        )
        self.left_name.config(text=left.name)
        self.right_name.config(text=right.name)
        self._show_image(self.left_canvas, left, side="left")
        self._show_image(self.right_canvas, right, side="right")

    def _show_image(self, canvas: tk.Canvas, path: Path, side: str) -> None:
        canvas.delete("all")
        try:
            image = Image.open(path).convert("RGBA")
        except Exception as exc:
            canvas.create_text(20, 20, text=str(exc), anchor="nw", fill="white")
            return

        canvas.update_idletasks()
        max_w = max(canvas.winfo_width(), 200)
        max_h = max(canvas.winfo_height(), 200)
        image.thumbnail((max_w - 20, max_h - 20), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        if side == "left":
            self.left_photo = photo
        else:
            self.right_photo = photo
        canvas.create_image(max_w // 2, max_h // 2, image=photo, anchor="center")

    def _delete_path(self, path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        remove_godot_import_files(path)
        remove_companion_base(path)

    def _move_to_pool(self, path: Path) -> None:
        if self.pool_dir is None:
            return
        target = self.pool_dir / path.name
        suffix = 1
        while target.exists():
            target = self.pool_dir / f"{path.stem}_{suffix}{path.suffix}"
            suffix += 1
        shutil.move(str(path), str(target))

    def _choose_winner(self, winner: Path, loser: Path) -> None:
        self._delete_path(loser)
        self.current_winner = winner
        self._load_next_pair()

    def _choose_side(self, side: str) -> None:
        if self.current_pair is None:
            return
        if side == "left":
            self._choose_winner(self.current_pair.left, self.current_pair.right)
        else:
            self._choose_winner(self.current_pair.right, self.current_pair.left)

    def _pool_pair(self) -> None:
        if self.current_pair is None:
            return
        self._move_to_pool(self.current_pair.left)
        self._move_to_pool(self.current_pair.right)
        self.current_winner = None
        self._load_next_pair()

    def _skip_pair(self) -> None:
        if self.current_pair is None:
            return
        self.queue.append(self.current_pair.left)
        self.queue.append(self.current_pair.right)
        self.current_winner = None
        self._load_next_pair()

    def _finish(self) -> None:
        self.status_var.set("Done. 残っている画像が1枚になりました。")
        self.pool_button.config(state="disabled")
        self.skip_button.config(state="disabled")
        self.current_pair = None
        messagebox.showinfo("Image Picker", "比較が完了しました。")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pick the better image from a folder, pair by pair.")
    parser.add_argument("folder", nargs="?", help="Folder containing image files")
    args = parser.parse_args()

    folder = None
    if args.folder:
        candidate = Path(args.folder).expanduser().resolve()
        if candidate.is_dir():
            folder = candidate
    else:
        cfg = load_config()
        favorites = cfg.get("favorites", DEFAULT_FAVORITES)
        if favorites:
            first = Path(favorites[0].get("path", "")).expanduser()
            if first.is_dir():
                folder = first

    root = tk.Tk()
    app = ImagePickerApp(root, folder)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
