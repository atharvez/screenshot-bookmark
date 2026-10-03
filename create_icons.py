"""Generate icons for the Screenshot Bookmark browser extension."""
from pathlib import Path
from PIL import Image, ImageDraw

def generate_icon(size: int, output_path: Path):
    """Draw a clean, modern extension icon with a camera and bookmark ribbon."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    padding = max(1, int(size * 0.08))
    radius = max(3, int(size * 0.22))

    # Base rounded rectangle background (Indigo / Blue gradient feel)
    bg_rect = [padding, padding, size - padding, size - padding]
    bg_color = (37, 99, 235, 255)  # #2563eb Blue
    draw.rounded_rectangle(bg_rect, radius=radius, fill=bg_color)

    # Scale factor
    s = size / 128.0

    # Camera body (White)
    cam_left = int(28 * s)
    cam_top = int(44 * s)
    cam_right = int(100 * s)
    cam_bottom = int(96 * s)
    cam_radius = max(2, int(8 * s))
    draw.rounded_rectangle([cam_left, cam_top, cam_right, cam_bottom], radius=cam_radius, fill=(255, 255, 255, 255))

    # Camera top bump / viewfinder
    bump_left = int(46 * s)
    bump_top = int(34 * s)
    bump_right = int(82 * s)
    bump_bottom = int(46 * s)
    draw.rounded_rectangle([bump_left, bump_top, bump_right, bump_bottom], radius=max(2, int(4 * s)), fill=(255, 255, 255, 255))

    # Camera lens circle
    center = (int(64 * s), int(70 * s))
    lens_radius = int(18 * s)
    draw.ellipse(
        [center[0] - lens_radius, center[1] - lens_radius, center[0] + lens_radius, center[1] + lens_radius],
        fill=(37, 99, 235, 255)
    )
    inner_radius = int(10 * s)
    draw.ellipse(
        [center[0] - inner_radius, center[1] - inner_radius, center[0] + inner_radius, center[1] + inner_radius],
        fill=(255, 255, 255, 255)
    )

    # Bookmark ribbon on top right (Amber / Gold)
    bm_left = int(82 * s)
    bm_right = int(106 * s)
    bm_top = int(14 * s)
    bm_bottom = int(58 * s)
    bm_notch = int(48 * s)
    bm_points = [
        (bm_left, bm_top),
        (bm_right, bm_top),
        (bm_right, bm_bottom),
        (int((bm_left + bm_right) / 2), bm_notch),
        (bm_left, bm_bottom)
    ]
    draw.polygon(bm_points, fill=(245, 158, 11, 255))  # #f59e0b Amber

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Generated {output_path} ({size}x{size})")

def main():
    icons_dir = Path(__file__).parent / "extension" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    for size in [16, 32, 48, 128]:
        out_file = icons_dir / f"icon{size}.png"
        generate_icon(size, out_file)

if __name__ == "__main__":
    main()
