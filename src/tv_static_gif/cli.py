"""Command-line interface."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import webbrowser

from . import __version__
from .generator import PRESETS, QUALITY, generate_tv_static


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate animated TV static.")
    parser.add_argument("output")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--width", type=int, default=820); parser.add_argument("--height", type=int, default=740)
    parser.add_argument("--duration", type=float, default=5); parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--background-fps", type=int); parser.add_argument("--text", default=None); parser.add_argument("--text-fps", type=int, default=6)
    parser.add_argument("--font"); parser.add_argument("--font-size", type=int, default=220); parser.add_argument("--text-position", choices=("top", "center", "bottom"), default="center")
    parser.add_argument("--no-auto-fit", action="store_true"); parser.add_argument("--image"); parser.add_argument("--image-fps", type=int); parser.add_argument("--image-position", choices=("top", "center", "bottom"), default="bottom"); parser.add_argument("--image-scale", type=float, default=.25)
    parser.add_argument("--preset", choices=tuple(PRESETS), default="crt"); parser.add_argument("--quality", choices=tuple(QUALITY), default="high"); parser.add_argument("--scale", type=float); parser.add_argument("--colors", type=int)
    parser.add_argument("--format", dest="output_format", choices=("gif", "webp", "apng")); parser.add_argument("--loop", type=int, default=0); parser.add_argument("--output-dir", type=Path); parser.add_argument("--seed", type=int); parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    output = (args.output_dir / Path(args.output).name) if args.output_dir else Path(args.output)
    params = vars(args); params.pop("output"); params.pop("output_dir"); preview = params.pop("preview"); params["font_path"] = params.pop("font"); params["image_path"] = params.pop("image"); params["auto_fit"] = not params.pop("no_auto_fit")
    path = generate_tv_static(output, **params)
    print(f"Created: {path}")
    if preview:
        if hasattr(os, "startfile"): os.startfile(path)  # type: ignore[attr-defined]
        else: webbrowser.open(path.resolve().as_uri())


if __name__ == "__main__": main()
