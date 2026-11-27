"""Generate Wanted posters by compositing member avatars onto the template."""
from io import BytesIO
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

# Approximate coordinates of the empty frame in the 1024×1536 template.
# These values are tuned for the provided western-style Wanted poster.
FRAME_LEFT = 180
FRAME_TOP = 380
FRAME_RIGHT = 844
FRAME_BOTTOM = 1040


def _template_path() -> Path:
    return Path(__file__).resolve().parent / "wanted_template.png"


def make_wanted_poster(avatar_path: Path | None, member_name: str = "") -> bytes:
    """
    Composite the member's avatar into the Wanted template and return JPEG bytes.
    If no avatar is available a neutral placeholder is used.
    """
    template = Image.open(_template_path()).convert("RGB")
    frame_w = FRAME_RIGHT - FRAME_LEFT
    frame_h = FRAME_BOTTOM - FRAME_TOP

    if avatar_path and avatar_path.is_file():
        try:
            avatar = Image.open(avatar_path).convert("RGB")
        except Exception:
            avatar = Image.new("RGB", (frame_w, frame_h), (40, 40, 40))
    else:
        avatar = Image.new("RGB", (frame_w, frame_h), (40, 40, 40))

    # Cover the frame while preserving aspect ratio
    avatar_ratio = avatar.width / avatar.height
    frame_ratio = frame_w / frame_h
    if avatar_ratio > frame_ratio:
        # avatar is wider → fit height
        new_h = frame_h
        new_w = int(new_h * avatar_ratio)
    else:
        new_w = frame_w
        new_h = int(new_w / avatar_ratio)
    avatar = avatar.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Center crop
    left = (new_w - frame_w) // 2
    top = (new_h - frame_h) // 2
    avatar = avatar.crop((left, top, left + frame_w, top + frame_h))

    template.paste(avatar, (FRAME_LEFT, FRAME_TOP))

    # Optional name under the frame. The runtime image ships no TrueType font and
    # the default bitmap font cannot encode Persian glyphs, so a missing font must
    # skip the name rather than abort poster generation. The member's name is shown
    # in the title list anyway.
    font = None
    if member_name:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        except Exception:
            font = None
    if font is not None:
        draw = ImageDraw.Draw(template)
        try:
            bbox = draw.textbbox((0, 0), member_name, font=font)
            text_w = bbox[2] - bbox[0]
            x = (template.width - text_w) // 2
            draw.text((x, FRAME_BOTTOM + 20), member_name, fill=(40, 20, 10), font=font)
        except Exception:
            pass

    buffer = BytesIO()
    template.save(buffer, format="JPEG", quality=88, optimize=True)
    return buffer.getvalue()
