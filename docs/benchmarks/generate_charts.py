#!/usr/bin/env python3
"""Generate the public benchmark SVGs from the checked-in result summary."""

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
    generate_full_chart()
    generate_causeloom_only_chart()


def write_svg(
    filename: str,
    width: int,
    height: int,
    body: list[str],
    title: str,
    desc: str,
) -> None:
    document = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{html.escape(title)}</title>',
            f'<desc id="desc">{html.escape(desc)}</desc>',
            f'<rect width="{width}" height="{height}" fill="{BG}"/>',
            *body,
            "</svg>",
            "",
        ]
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / filename).write_text(document, encoding="utf-8", newline="\n")
    print(f"Wrote {filename}")


def generate_full_chart() -> None:
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
    write_svg(
        "benchmark-full.svg",
        width,
        height,
        body,
        "13-task benchmark results",
        section["description"],
    )


def generate_causeloom_only_chart() -> None:
    section = DATA["causeloom_only_successes"]
    rows = section["tasks"]
    width, height = 960, 470
    left, right, top = 285, 95, 125
    plot_width = width - left - right
    row_gap = 68
    body = [
        text(48, 48, "Tasks with Causeloom-only successes", size=26, weight=700),
        text(
            48,
            78,
            "Official reward-1 attempts out of 3 - contemporaneous a5 cells",
            size=15,
            fill=MUTED,
        ),
    ]
    for tick in range(4):
        x = left + plot_width * tick / 3
        body.append(
            f'<line x1="{x}" y1="{top - 8}" x2="{x}" y2="{height - 62}" stroke="{GRID}"/>'
        )
        body.append(
            text(x, height - 39, str(tick), size=13, fill=MUTED, anchor="middle")
        )

    for index, row in enumerate(rows):
        y = top + index * row_gap
        body.append(
            text(
                left - 18,
                y + 23,
                row["label"],
                size=16,
                weight=600,
                anchor="end",
            )
        )
        for offset, key, color in (
            (0, "baseline_reward_1", GREY),
            (24, "causeloom_reward_1", BLUE),
        ):
            value = row[key]
            bar_width = plot_width * value / 3
            body.append(
                f'<rect x="{left}" y="{y + offset}" width="{bar_width}" '
                f'height="18" rx="3" fill="{color}"/>'
            )
            label_x = left + bar_width + 9
            body.append(
                text(label_x, y + offset + 14, f"{value}/3", size=13, weight=600)
            )

    legend_y = height - 10
    body.extend(
        [
            f'<rect x="{left}" y="{legend_y - 13}" width="14" height="14" rx="2" fill="{GREY}"/>',
            text(left + 22, legend_y, "No-skill baseline", size=12, fill=MUTED),
            f'<rect x="{left + 155}" y="{legend_y - 13}" width="14" height="14" rx="2" fill="{BLUE}"/>',
            text(left + 177, legend_y, "Causeloom", size=12, fill=MUTED),
            text(
                width - right,
                legend_y,
                "Doom reward-1 is timeout-flagged",
                size=12,
                fill=MUTED,
                anchor="end",
            ),
        ]
    )
    write_svg(
        "benchmark-causeloom-only-wins.svg",
        width,
        height,
        body,
        "Tasks with Causeloom-only successes",
        section["description"],
    )


if __name__ == "__main__":
    main()
