"""Create animated TV-static files."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Callable, Optional, Union

from PIL import Image, ImageChops, ImageDraw, ImageFont

PathLike = Union[str, Path]
ProgressCallback = Callable[[int, int], None]

PRESETS = {
    "clean": {"scanlines": 0, "flicker": 0, "jitter": 0, "glitch": 0},
    "crt": {"scanlines": 4, "flicker": 8, "jitter": 1, "glitch": 0},
    "weak-signal": {"scanlines": 3, "flicker": 24, "jitter": 3, "glitch": 3},
    "vhs": {"scanlines": 4, "flicker": 14, "jitter": 2, "glitch": 8},
}
QUALITY = {"low": (0.5, 64), "medium": (0.75, 128), "high": (1.0, 256)}


def _font(path: Optional[PathLike], size: int) -> ImageFont.ImageFont:
    if path is not None:
        try:
            return ImageFont.truetype(str(path), size)
        except OSError as error:
            raise ValueError(f"could not load font: {path}") from error
    for name in ("DejaVuSans-Bold.ttf", "Arial.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _position(size: tuple[int, int], content: tuple[int, int], where: str) -> tuple[int, int]:
    width, height = size
    content_width, content_height = content
    x = (width - content_width) // 2
    if where == "top":
        return x, max(0, height // 20)
    if where == "bottom":
        return x, max(0, height - content_height - height // 20)
    return x, (height - content_height) // 2


def _text_mask(
    size: tuple[int, int], text: Optional[str], font_path: Optional[PathLike],
    font_size: int, position: str, auto_fit: bool,
) -> Optional[Image.Image]:
    if not text:
        return None
    font = _font(font_path, font_size)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    box = probe.multiline_textbbox((0, 0), text, font=font, align="center")
    if auto_fit and box[2] - box[0] > size[0] * 0.9 and font_size > 8:
        font = _font(font_path, max(8, int(font_size * size[0] * 0.9 / (box[2] - box[0]))))
        box = probe.multiline_textbbox((0, 0), text, font=font, align="center")
    mask = Image.new("L", size)
    draw = ImageDraw.Draw(mask)
    xy = _position(size, (box[2] - box[0], box[3] - box[1]), position)
    draw.multiline_text((xy[0] - box[0], xy[1] - box[1]), text, font=font, fill=255, align="center")
    return mask


def _image_mask(path: Optional[PathLike], size: tuple[int, int], position: str, scale: float) -> Optional[Image.Image]:
    if path is None:
        return None
    try:
        source = Image.open(path).convert("RGBA")
    except OSError as error:
        raise ValueError(f"could not load image: {path}") from error
    max_size = (max(1, int(size[0] * scale)), max(1, int(size[1] * scale)))
    source.thumbnail(max_size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size)
    mask.paste(source.getchannel("A"), _position(size, source.size, position))
    return mask


def _pattern(size: tuple[int, int], rng: random.Random, preset: dict[str, int], colors: int) -> Image.Image:
    width, height = size
    pixels = bytearray(rng.randbytes(width * height))
    if colors < 256:
        step = 256 // colors
        for index, value in enumerate(pixels):
            pixels[index] = (value // step) * step
    step = preset["scanlines"]
    if step:
        for y in range(0, height, step):
            start, end = y * width, (y + 1) * width
            pixels[start:end] = bytes(value // 2 for value in pixels[start:end])
    image = Image.frombytes("L", size, bytes(pixels))
    if preset["flicker"]:
        image = ImageChops.subtract(image, Image.new("L", size, rng.randrange(preset["flicker"])))
    if preset["jitter"]:
        image = ImageChops.offset(image, rng.randrange(-preset["jitter"], preset["jitter"] + 1), 0)
    if preset["glitch"]:
        for _ in range(2):
            y = rng.randrange(height)
            band = image.crop((0, y, width, min(height, y + rng.randrange(1, preset["glitch"] + 1))))
            image.paste(ImageChops.offset(band, rng.randrange(-preset["glitch"], preset["glitch"] + 1), 0), (0, y))
    return image


def _format(destination: Path, requested: Optional[str]) -> tuple[Path, str]:
    aliases = {"gif": (".gif", "GIF"), "webp": (".webp", "WEBP"), "apng": (".png", "PNG")}
    key = (requested or {".webp": "webp", ".png": "apng"}.get(destination.suffix.lower(), "gif")).lower()
    if key not in aliases:
        raise ValueError("output_format must be gif, webp or apng")
    suffix, pillow_format = aliases[key]
    return destination.with_suffix(suffix), pillow_format


def generate_tv_static(
    output: PathLike, *, width: int = 820, height: int = 740, duration: float = 5,
    fps: int = 24, background_fps: Optional[int] = None, text: Optional[str] = None,
    text_fps: int = 6, font_path: Optional[PathLike] = None, font_size: int = 220,
    text_position: str = "center", auto_fit: bool = True, image_path: Optional[PathLike] = None,
    image_fps: Optional[int] = None, image_position: str = "bottom", image_scale: float = 0.25,
    preset: str = "crt", quality: str = "high", scale: Optional[float] = None,
    colors: Optional[int] = None, output_format: Optional[str] = None, loop: int = 0,
    seed: Optional[int] = None, progress: Optional[ProgressCallback] = None,
) -> Path:
    """Generate TV static in GIF, animated WebP, or APNG format."""
    if width < 1 or height < 1 or duration <= 0 or not 1 <= fps <= 100:
        raise ValueError("width/height must be positive, duration positive, and fps between 1 and 100")
    if preset not in PRESETS or quality not in QUALITY:
        raise ValueError(f"preset must be one of {', '.join(PRESETS)}; quality must be one of {', '.join(QUALITY)}")
    if text_position not in {"top", "center", "bottom"} or image_position not in {"top", "center", "bottom"}:
        raise ValueError("positions must be top, center or bottom")
    if not 1 <= text_fps <= fps or (image_fps is not None and not 1 <= image_fps <= fps):
        raise ValueError("text_fps and image_fps must be between 1 and fps")
    bg_fps = background_fps or fps
    if not 1 <= bg_fps <= fps or font_size < 1 or image_scale <= 0 or loop < 0:
        raise ValueError("invalid speed, font_size, image_scale or loop")
    quality_scale, quality_colors = QUALITY[quality]
    actual_scale = quality_scale if scale is None else scale
    if actual_scale <= 0:
        raise ValueError("scale must be positive")
    size = (max(1, round(width * actual_scale)), max(1, round(height * actual_scale)))
    palette_colors = quality_colors if colors is None else colors
    if not 2 <= palette_colors <= 256:
        raise ValueError("colors must be between 2 and 256")
    destination, pillow_format = _format(Path(output), output_format)
    destination.parent.mkdir(parents=True, exist_ok=True)
    text_mask = _text_mask(size, text, font_path, max(1, round(font_size * actual_scale)), text_position, auto_fit)
    image_mask = _image_mask(image_path, size, image_position, image_scale)
    count, rng = max(1, round(duration * fps)), random.Random(seed)
    durations = [((index + 1) * round(duration * 100) // count - index * round(duration * 100) // count) * 10 for index in range(count)]
    current_bg = current_text = current_image = None
    seen_bg = seen_text = seen_image = -1
    frames: list[Image.Image] = []
    for index in range(count):
        key = index * bg_fps // fps
        if key != seen_bg:
            current_bg, seen_bg = _pattern(size, rng, PRESETS[preset], palette_colors), key
        if text_mask is not None and index * text_fps // fps != seen_text:
            current_text, seen_text = _pattern(size, rng, PRESETS[preset], palette_colors), index * text_fps // fps
        effective_image_fps = image_fps or text_fps
        if image_mask is not None and index * effective_image_fps // fps != seen_image:
            current_image, seen_image = _pattern(size, rng, PRESETS[preset], palette_colors), index * effective_image_fps // fps
        frame = current_bg.copy()
        if text_mask is not None and current_text is not None:
            frame = Image.composite(current_text, frame, text_mask)
        if image_mask is not None and current_image is not None:
            frame = Image.composite(current_image, frame, image_mask)
        frames.append(frame)
        if progress:
            progress(index + 1, count)
    save_frames = [frame.convert("P", colors=palette_colors) if pillow_format == "GIF" else frame for frame in frames]
    save_options = {
        "format": pillow_format,
        "save_all": True,
        "append_images": save_frames[1:],
        "duration": durations,
        "loop": loop,
    }
    if pillow_format == "GIF":
        save_options.update({"optimize": False, "disposal": 2})
    elif pillow_format == "WEBP":
        save_options.update({"lossless": True, "method": 6})
    else:  # APNG
        save_options.update({"disposal": 0, "blend": 0})
    save_frames[0].save(destination, **save_options)
    return destination


def generate_tv_static_gif(output: PathLike, **kwargs: object) -> Path:
    """Backward-compatible GIF-only wrapper around :func:`generate_tv_static`."""
    kwargs["output_format"] = "gif"
    return generate_tv_static(output, **kwargs)  # type: ignore[arg-type]
