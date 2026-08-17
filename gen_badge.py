#!/usr/bin/env python3
"""Generate a coverage badge SVG from coverage.xml."""

import xml.etree.ElementTree as ET
from pathlib import Path


def generate_badge(coverage_xml: str = "coverage.xml", output: str = "docs/coverage.svg") -> None:
    root = ET.parse(coverage_xml).getroot()
    rate = float(root.get("line-rate", "0"))
    pct = round(rate * 100, 1)
    if pct >= 80:
        color = "brightgreen"
    elif pct >= 70:
        color = "green"
    elif pct >= 60:
        color = "yellowgreen"
    elif pct >= 50:
        color = "yellow"
    elif pct >= 40:
        color = "orange"
    else:
        color = "red"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="104" height="20" role="img" aria-label="coverage: {pct}%">  # noqa: E501  # Line too long (intentional)
  <title>coverage: {pct}%</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="104" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="63" height="20" fill="#555"/>
    <rect x="63" width="41" height="20" fill="{color}"/>
    <rect width="104" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">  # noqa: E501  # Line too long (intentional)
    <text x="31.5" y="14">coverage</text>
    <text x="83.5" y="14">{pct}%</text>
  </g>
</svg>"""

    Path(output).write_text(svg, encoding="utf-8")
    print(f"wrote {output}: {pct}% ({color})")


if __name__ == "__main__":
    generate_badge()
