"""Render only recorded P3 calibration values into a README SVG figure."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "evidence" / "p3_kick_calibration_pilot_3x3_r2" / "kick_calibration_pilot.csv"
OUTPUT = ROOT / "media" / "visuals" / "p3_kick_calibration_pilot.svg"


def color(value):
    # A neutral-to-orange scale; color encodes measured displacement only.
    strength = min(1.0, value / 0.15)
    return f"rgb(255,{int(245 - 130 * strength)},{int(235 - 175 * strength)})"


def main():
    with INPUT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 9 or any(row.get("ball_velocity_injected") != "False" for row in rows):
        raise RuntimeError("expected nine non-injected real calibration rows")
    forwards = sorted({float(row["forward_offset_m"]) for row in rows})
    laterals = sorted({float(row["lateral_offset_m"]) for row in rows}, reverse=True)
    lookup = {(float(row["forward_offset_m"]), float(row["lateral_offset_m"])): row for row in rows}
    x0, y0, cell = 190, 105, 130
    pieces = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="700" height="600" viewBox="0 0 700 600">',
        '<style>text{font-family:Arial,sans-serif;fill:#172033}.title{font-size:22px;font-weight:bold}.small{font-size:13px}.value{font-size:18px;font-weight:bold}</style>',
        '<rect width="700" height="600" fill="#ffffff"/>',
        '<text x="30" y="38" class="title">P3 real Webots pilot: ball displacement</text>',
        '<text x="30" y="63" class="small">3×3 placement scan · 6 s per cell · no ball-velocity injection · all rows remain evidence-insufficient</text>',
        '<text x="30" y="86" class="small">Colour is measured max displacement only; it is not a kick-success score.</text>',
        '<text x="30" y="300" class="small" transform="rotate(-90 30 300)">lateral offset (m)</text>',
        '<text x="360" y="535" class="small">forward offset (m)</text>',
    ]
    for col, forward in enumerate(forwards):
        pieces.append(f'<text x="{x0 + col * cell + 43}" y="95" class="small">{forward:.2f}</text>')
    for row_i, lateral in enumerate(laterals):
        y = y0 + row_i * cell
        pieces.append(f'<text x="145" y="{y + 68}" class="small">{lateral:.2f}</text>')
        for col, forward in enumerate(forwards):
            item = lookup[(forward, lateral)]
            value = float(item["max_ball_displacement_m"])
            x = x0 + col * cell
            pieces.extend([
                f'<rect x="{x}" y="{y}" width="116" height="116" rx="8" fill="{color(value)}" stroke="#a8b0c0"/>',
                f'<text x="{x + 18}" y="{y + 50}" class="value">{value:.4f} m</text>',
                f'<text x="{x + 12}" y="{y + 76}" class="small">{item["evidence_status"]}</text>',
                f'<text x="{x + 12}" y="{y + 96}" class="small">kick req: {item["kick_requests"]}</text>',
            ])
    pieces.extend([
        '<rect x="30" y="555" width="16" height="16" fill="rgb(255,245,235)"/><text x="52" y="568" class="small">0 m</text>',
        '<rect x="115" y="555" width="16" height="16" fill="rgb(255,115,60)"/><text x="137" y="568" class="small">≥0.15 m</text>',
        '<text x="250" y="568" class="small">Strict P3 gate additionally requires toe contact during kick motion.</text>',
        '</svg>',
    ])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(pieces), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
