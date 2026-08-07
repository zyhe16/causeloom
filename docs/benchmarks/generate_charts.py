#!/usr/bin/env python3
"""Generate the public benchmark SVG from the checked-in result summary."""

from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
OUTPUT = ROOT.parent / "assets"

INK = "#172033"
MUTED = "#667085"
GRID = "#D9E0EA"
BLUE = "#356AE6"
GREY = "#A7B0BF"
BG = "#FFFFFF"


def text(
    x: float,
    y: float,
    value: str,
    *,
    size: int = 16,
    weight: int = 400,
    fill: str = INK,
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="Inter,Segoe UI,Arial,sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{html.escape(value)}</text>'
    )


def main() -> None:
    section = DATA["full_13_task_context"]
    rows = section["conditions"]
    width, height = 960, 350
    left, right, top = 220, 90, 125
    plot_width = width - left - right
    body = [
        text(48, 48, "13-task benchmark results", size=26, weight=700),
        text(48, 78, "13 tasks x 3 repetitions - 39 attempts per condition", size=15, fill=MUTED),
    ]
    for tick in (0, 20, 40, 60, 80, 100):
        x = left + plot_width * tick / 100
        body.append(
            f'<line x1="{x}" y1="{top - 8}" x2="{x}" y2="{height - 75}" stroke="{GRID}"/>'
        )
        body.append(text(x, height - 49, f"{tick}%", size=13, fill=MUTED, anchor="middle"))
    for index, row in enumerate(rows):
        y = top + index * 70
        rate = 100 * row["reward_1"] / row["runs"]
        color = BLUE if row["name"] == "Causeloom" else GREY
        body.append(text(left - 18, y + 24, row["name"], size=17, weight=600, anchor="end"))
        body.append(
            f'<rect x="{left}" y="{y}" width="{plot_width * rate / 100}" '
            f'height="32" rx="3" fill="{color}"/>'
        )
        body.append(
            text(
                left + plot_width * rate / 100 + 10,
                y + 23,
                f'{row["reward_1"]}/39 - {rate:.1f}%',
                size=14,
                weight=600,
            )
        )
    body.append(
        text(
            48,
            height - 14,
            "Two-phase descriptive view: 12 baseline cells use the earlier a3 timeout contract.",
            size=12,
            fill=MUTED,
        )
    )
    document = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            '<title id="title">13-task benchmark results</title>',
            f'<desc id="desc">{html.escape(section["description"])}</desc>',
            f'<rect width="{width}" height="{height}" fill="{BG}"/>',
            *body,
            "</svg>",
            "",
        ]
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "benchmark-full.svg").write_text(document, encoding="utf-8", newline="\n")
    print("Wrote benchmark-full.svg")


if __name__ == "__main__":
    main()
