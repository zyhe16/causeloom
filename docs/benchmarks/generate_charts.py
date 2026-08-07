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
BLUE = "#2457D6"
GREY = "#7A8494"
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


def add_percent_grid(
    body: list[str], *, left: int, plot_width: int, top: int, bottom: int
) -> None:
    for tick in (0, 20, 40, 60, 80, 100):
        x = left + plot_width * tick / 100
        body.append(
            f'<line x1="{x}" y1="{top}" x2="{x}" y2="{bottom}" stroke="{GRID}"/>'
        )
        body.append(text(x, bottom + 23, f"{tick}%", size=13, fill=MUTED, anchor="middle"))


def generate_full_chart() -> None:
    section = DATA["matched_13_task_result"]
    rows = section["conditions"]
    width, height = 960, 350
    left, right, top = 220, 85, 125
    plot_width = width - left - right
    body = [
        text(48, 48, "Causeloom completed 7 more runs", size=26, weight=700),
        text(
            48,
            78,
            "Official verifier passes · 13 tasks × 3 repetitions per condition",
            size=15,
            fill=MUTED,
        ),
    ]
    add_percent_grid(body, left=left, plot_width=plot_width, top=top - 8, bottom=265)
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
                f'{row["reward_1"]}/{row["runs"]} · {rate:.1f}%',
                size=14,
                weight=600,
            )
        )
    body.append(
        text(
            48,
            height - 14,
            "GPT-5.6 Luna Max · matched execution contract · 0 timeouts · automated reward",
            size=12,
            fill=MUTED,
        )
    )
    write_svg(
        "benchmark-full.svg",
        width,
        height,
        body,
        "Matched 13-task benchmark results",
        section["description"],
    )


def generate_category_chart() -> None:
    rows = DATA["category_results"]
    width, height = 960, 470
    # Keep a fixed label gutter after the 100% grid line. Some Markdown
    # renderers clip SVG overflow instead of honoring text beyond the plot.
    left, right, top = 250, 240, 120
    plot_width = width - left - right
    body = [
        text(48, 48, "The largest gain was on extreme systems", size=26, weight=700),
        text(48, 78, "Official verifier pass rate within each task category", size=15, fill=MUTED),
    ]
    add_percent_grid(body, left=left, plot_width=plot_width, top=top - 8, bottom=390)
    for index, row in enumerate(rows):
        y = top + index * 86
        body.append(
            text(left - 18, y + 28, row["category"], size=16, weight=600, anchor="end")
        )
        for offset, key, label, color in (
            (0, "baseline_reward_1", "Baseline", GREY),
            (31, "causeloom_reward_1", "Causeloom", BLUE),
        ):
            value = row[key]
            total = row["runs_per_condition"]
            rate = 100 * value / total
            bar_width = plot_width * rate / 100
            body.append(
                f'<rect x="{left}" y="{y + offset}" width="{bar_width}" '
                f'height="22" rx="3" fill="{color}"/>'
            )
            body.append(
                text(
                    left + bar_width + 9,
                    y + offset + 16,
                    f"{label} {value}/{total} · {rate:.1f}%",
                    size=13,
                    weight=600,
                )
            )
    body.append(
        text(
            48,
            height - 14,
            "Categories are preregistered in evals/research-suite.csv; all use the same matched run contract.",
            size=12,
            fill=MUTED,
        )
    )
    write_svg(
        "benchmark-luna-by-category.svg",
        width,
        height,
        body,
        "Matched benchmark results by task category",
        "Causeloom versus the no-skill baseline across integration and build, extreme systems, and targeted coverage tasks.",
    )


def generate_causeloom_only_chart() -> None:
    section = DATA["causeloom_only_successes"]
    rows = section["tasks"]
    width, height = 960, 340
    # Reserve room for direct labels after the maximum value.
    left, right, top = 285, 190, 125
    plot_width = width - left - right
    body = [
        text(48, 48, "Causeloom broke two baseline deadlocks", size=26, weight=700),
        text(48, 78, "Official verifier passes out of 3 matched attempts", size=15, fill=MUTED),
    ]
    for tick in range(4):
        x = left + plot_width * tick / 3
        body.append(
            f'<line x1="{x}" y1="{top - 8}" x2="{x}" y2="{height - 65}" stroke="{GRID}"/>'
        )
        body.append(text(x, height - 42, str(tick), size=13, fill=MUTED, anchor="middle"))

    for index, row in enumerate(rows):
        y = top + index * 78
        body.append(text(left - 18, y + 28, row["label"], size=16, weight=600, anchor="end"))
        for offset, key, label, color in (
            (0, "baseline_reward_1", "Baseline", GREY),
            (27, "causeloom_reward_1", "Causeloom", BLUE),
        ):
            value = row[key]
            bar_width = plot_width * value / 3
            body.append(
                f'<rect x="{left}" y="{y + offset}" width="{bar_width}" '
                f'height="20" rx="3" fill="{color}"/>'
            )
            body.append(
                text(
                    left + bar_width + 9,
                    y + offset + 15,
                    f"{label} {value}/3",
                    size=13,
                    weight=600,
                )
            )
    write_svg(
        "benchmark-luna-only-wins.svg",
        width,
        height,
        body,
        "Tasks solved only by Causeloom",
        section["description"],
    )


def main() -> None:
    generate_full_chart()
    generate_category_chart()
    generate_causeloom_only_chart()


if __name__ == "__main__":
    main()
