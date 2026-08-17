#!/usr/bin/env python3
"""Generate a coverage.svg badge from coverage.json written by pytest-cov."""

import json
import sys
from pathlib import Path


def generate(coverage_json: Path, output_svg: Path) -> float:
    data = json.loads(coverage_json.read_text(encoding="utf-8"))
    percent = float(data["totals"]["percent_covered"])

    if percent >= 80:
        color = "brightgreen"
    elif percent >= 60:
        color = "yellow"
    else:
        color = "red"

    label = "coverage"
    value = f"{percent:.1f}%"

    # Shield-style SVG dimensions
    label_w = 61
    value_w = 55
    total_w = label_w + value_w

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{total_w}" height="20" role="img" aria-label="{label}: {value}">\n'
        f"  <title>{label}: {value}</title>\n"
        f'  <linearGradient id="s" x2="0" y2="100%">\n'
        f'    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>\n'
        f'    <stop offset="1" stop-opacity=".1"/>\n'
        f"  </linearGradient>\n"
        f'  <clipPath id="r"><rect width="{total_w}" height="20" rx="3" fill="#fff"/></clipPath>\n'
        f'  <g clip-path="url(#r)">\n'
        f'    <rect width="{label_w}" height="20" fill="#555"/>\n'
        f'    <rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>\n'
        f'    <rect width="{total_w}" height="20" fill="url(#s)"/>\n'
        f"  </g>\n"
        f'  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">\n'  # noqa: E501  # Line too long (intentional)
        f'    <text x="{label_w / 2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>\n'
        f'    <text x="{label_w / 2}" y="14">{label}</text>\n'
        f'    <text x="{
            label_w +
            value_w /
            2}" y="15" fill="#010101" fill-opacity=".3">{value}</text>\n'
        f'    <text x="{label_w + value_w / 2}" y="14">{value}</text>\n'
        f"  </g>\n"
        f"</svg>\n"
    )

    output_svg.write_text(svg, encoding="utf-8")
    return percent


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    pct = generate(root / "coverage.json", root / "coverage.svg")
    print(f"Generated coverage.svg with {pct:.2f}% coverage")
    sys.exit(0)
