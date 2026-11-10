"""Section heading images for the profile README, set in Paperlogy.

Text is converted to outlines (same helper as the banner), so the images look
the same everywhere. Each heading gets a light and a dark version for GitHub's
<picture> theme switch.

    python3 -B scripts/make_headings.py -o assets/headings
"""
import argparse
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_banner import text_outline  # noqa: E402

HEADINGS = {
    "about": "About",
    "tech-stack": "Tech Stack",
    "publications": "Publications & Talks",
    "projects": "Featured Projects",
    "awards": "Awards",
}
TEXT = {"light": "#1f2328", "dark": "#f0f6fc"}  # GitHub body text per theme
ACCENT = "#3e8e48"                              # pitch green from the banner
SIZE, HEIGHT, BASELINE = 26, 36, 27
BAR_W, GAP = 6, 12


def heading_svg(text, color, font):
    d, w = text_outline(font, text, SIZE)
    width = round(BAR_W + GAP + w + 2)
    label = html.escape(text)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{HEIGHT}" '
        f'viewBox="0 0 {width} {HEIGHT}" role="img" aria-label="{label}">'
        f"<title>{label}</title>"
        f'<rect x="0" y="6" width="{BAR_W}" height="{HEIGHT - 12}" rx="3" fill="{ACCENT}"/>'
        f'<path transform="translate({BAR_W + GAP},{BASELINE})" fill="{color}" d="{d}"/>'
        "</svg>\n"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="assets/headings")
    ap.add_argument("--font", default="/root/.fonts/Paperlogy-7Bold.ttf")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for key, text in HEADINGS.items():
        for theme, color in TEXT.items():
            with open(os.path.join(args.out, f"{key}-{theme}.svg"), "w", encoding="utf-8") as f:
                f.write(heading_svg(text, color, args.font))


if __name__ == "__main__":
    main()
