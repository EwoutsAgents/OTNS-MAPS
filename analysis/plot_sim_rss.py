#!/usr/bin/env python3
"""Generate dependency-free SVG plots for per-ping simulator RSS artifacts."""

from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
from typing import Any


COLORS = {
    "router_a_to_mobile": "#1f77b4",
    "router_b_to_mobile": "#2ca02c",
    "mobile_to_parent": "#d62728",
    "parent": "#555555",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Plot RSS over time for one baseline CSV.")
    run.add_argument("csv_file", type=Path)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--title", default=None)

    matrix = subparsers.add_parser("matrix", help="Plot aggregate end-dwell RSS for repeated artifacts.")
    matrix.add_argument("artifacts", nargs="+", type=Path)
    matrix.add_argument("--output", type=Path, required=True)
    matrix.add_argument("--title", default="End-dwell simulator RSS by repeated arm")
    return parser.parse_args()


def to_float(value: str | None) -> float | None:
    if value in (None, "", "None"):
        return None
    return float(value)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def points_to_path(points: list[tuple[float, float]], x_scale, y_scale) -> str:
    parts = []
    for index, (x_value, y_value) in enumerate(points):
        command = "M" if index == 0 else "L"
        parts.append(f"{command}{x_scale(x_value):.2f},{y_scale(y_value):.2f}")
    return " ".join(parts)


def write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def axis_ticks(min_value: float, max_value: float, count: int = 5) -> list[float]:
    if min_value == max_value:
        return [min_value]
    step = (max_value - min_value) / (count - 1)
    return [min_value + index * step for index in range(count)]


def plot_run(csv_file: Path, output: Path, title: str | None) -> None:
    rows = load_rows(csv_file)
    if not rows:
        raise ValueError(f"No rows in {csv_file}")

    series: dict[str, list[tuple[float, float]]] = {}
    for prefix in ("router_a_to_mobile", "router_b_to_mobile", "mobile_to_parent"):
        column = f"{prefix}_request_rx_sim_rss_dbm"
        values = []
        for row in rows:
            x_value = to_float(row.get("sim_time_s"))
            y_value = to_float(row.get(column))
            if x_value is not None and y_value is not None:
                values.append((x_value, y_value))
        if values:
            series[prefix] = values

    if not series:
        raise ValueError(f"No simulator RSS columns found in {csv_file}")

    width, height = 1040, 560
    left, right, top, bottom = 82, 28, 54, 74
    plot_width = width - left - right
    plot_height = height - top - bottom
    all_x = [x for values in series.values() for x, _ in values]
    all_y = [y for values in series.values() for _, y in values]
    min_x, max_x = min(all_x), max(all_x)
    min_y = min(-90.0, min(all_y) - 4)
    max_y = max(-40.0, max(all_y) + 4)

    def x_scale(value: float) -> float:
        return left + ((value - min_x) / (max_x - min_x or 1)) * plot_width

    def y_scale(value: float) -> float:
        return top + ((max_y - value) / (max_y - min_y or 1)) * plot_height

    title_text = title or csv_file.stem
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="28" font-family="Arial, sans-serif" font-size="20" font-weight="700">{html.escape(title_text)}</text>',
        f'<text x="{left}" y="48" font-family="Arial, sans-serif" font-size="12" fill="#555">Request-side simulator RSS, model-derived at ping event positions</text>',
    ]

    for tick in axis_ticks(min_y, max_y):
        y = y_scale(tick)
        elements.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.2f}" y2="{y:.2f}" stroke="#e5e5e5"/>')
        elements.append(
            f'<text x="{left-10}" y="{y+4:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#555">{tick:.0f}</text>'
        )
    for tick in axis_ticks(min_x, max_x):
        x = x_scale(tick)
        elements.append(f'<line x1="{x:.2f}" x2="{x:.2f}" y1="{top}" y2="{height-bottom}" stroke="#f0f0f0"/>')
        elements.append(
            f'<text x="{x:.2f}" y="{height-bottom+22}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#555">{tick:.0f}</text>'
        )

    elements.append(f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" fill="none" stroke="#222"/>')
    elements.append(
        f'<text x="20" y="{top+plot_height/2:.2f}" transform="rotate(-90 20,{top+plot_height/2:.2f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="13">RSS (dBm)</text>'
    )
    elements.append(
        f'<text x="{left+plot_width/2:.2f}" y="{height-20}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13">Simulation time (s)</text>'
    )

    legend_x = left + 12
    legend_y = top + 18
    for index, (name, values) in enumerate(series.items()):
        color = COLORS[name]
        path_data = points_to_path(values, x_scale, y_scale)
        elements.append(f'<path d="{path_data}" fill="none" stroke="{color}" stroke-width="2"/>')
        y = legend_y + index * 20
        elements.append(f'<line x1="{legend_x}" x2="{legend_x+24}" y1="{y}" y2="{y}" stroke="{color}" stroke-width="3"/>')
        elements.append(
            f'<text x="{legend_x+32}" y="{y+4}" font-family="Arial, sans-serif" font-size="12" fill="#222">{html.escape(name)}</text>'
        )

    parent_points = [
        (to_float(row.get("sim_time_s")), row.get("parent_node_guess"))
        for row in rows
        if row.get("parent_node_guess")
    ]
    switch_times = [
        to_float(row.get("sim_time_s"))
        for row in rows
        if str(row.get("parent_switch")).lower() in {"1", "true", "yes"}
    ]
    for switch_time in switch_times:
        if switch_time is None:
            continue
        x = x_scale(switch_time)
        elements.append(f'<line x1="{x:.2f}" x2="{x:.2f}" y1="{top}" y2="{height-bottom}" stroke="#111" stroke-dasharray="5 4"/>')
        elements.append(
            f'<text x="{x+5:.2f}" y="{top+14}" font-family="Arial, sans-serif" font-size="11" fill="#111">switch</text>'
        )
    if parent_points:
        final_parent = parent_points[-1][1]
        elements.append(
            f'<text x="{width-right}" y="{top-8}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#555">final parent: {html.escape(str(final_parent))}</text>'
        )

    elements.append("</svg>")
    write_svg(output, "\n".join(elements) + "\n")


def label_for_artifact(path: Path) -> str:
    parts = path.parts
    name = path.parent.name if path.name.endswith("experiment") else path.name
    collection = path.parent.name if path.name.endswith("experiment") else path.name
    if "results" in parts:
        idx = parts.index("results")
        if idx + 1 < len(parts):
            collection = parts[idx + 1]
    label = collection
    for prefix, profile in (
        ("med_simple_parent_switch_", "MED "),
        ("fed_simple_parent_switch_", "FED "),
        ("sed_simple_parent_switch_", "SED "),
    ):
        label = label.replace(prefix, profile)
    label = label.replace("-repeated", "").replace("pps-", "PPS ")
    return label


def load_aggregate(path: Path) -> dict[str, Any]:
    data = json.loads((path / "aggregate_summary.json").read_text(encoding="utf-8"))
    return data["aggregate"]


def plot_matrix(artifacts: list[Path], output: Path, title: str) -> None:
    rows = []
    for artifact in artifacts:
        aggregate = load_aggregate(artifact)
        rows.append(
            {
                "label": label_for_artifact(artifact),
                "router_a": aggregate.get("mean_router_a_to_mobile_end_dwell_sim_rss_dbm"),
                "mobile_parent": aggregate.get("mean_mobile_to_parent_end_dwell_sim_rss_dbm"),
            }
        )

    width, height = 1180, 560
    left, right, top, bottom = 84, 30, 58, 128
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [value for row in rows for value in (row["router_a"], row["mobile_parent"]) if value is not None]
    min_y = min(-90.0, min(values) - 4)
    max_y = max(-40.0, max(values) + 4)

    def y_scale(value: float) -> float:
        return top + ((max_y - value) / (max_y - min_y or 1)) * plot_height

    group_width = plot_width / max(1, len(rows))
    bar_width = min(54, group_width * 0.28)

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="30" font-family="Arial, sans-serif" font-size="20" font-weight="700">{html.escape(title)}</text>',
        f'<text x="{left}" y="50" font-family="Arial, sans-serif" font-size="12" fill="#555">Mean request-side RSS during end dwell, model-derived at ping event positions</text>',
    ]
    for tick in axis_ticks(min_y, max_y):
        y = y_scale(tick)
        elements.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.2f}" y2="{y:.2f}" stroke="#e5e5e5"/>')
        elements.append(
            f'<text x="{left-10}" y="{y+4:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#555">{tick:.0f}</text>'
        )
    elements.append(f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" fill="none" stroke="#222"/>')
    elements.append(
        f'<text x="22" y="{top+plot_height/2:.2f}" transform="rotate(-90 22,{top+plot_height/2:.2f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="13">RSS (dBm)</text>'
    )

    baseline = y_scale(min_y)
    for index, row in enumerate(rows):
        cx = left + group_width * index + group_width / 2
        for offset, key, color in ((-bar_width / 1.8, "router_a", COLORS["router_a_to_mobile"]), (bar_width / 1.8, "mobile_parent", COLORS["mobile_to_parent"])):
            value = row[key]
            if value is None:
                continue
            x = cx + offset - bar_width / 2
            y = y_scale(float(value))
            elements.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{baseline-y:.2f}" fill="{color}"/>')
            elements.append(
                f'<text x="{x+bar_width/2:.2f}" y="{y-5:.2f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="#222">{float(value):.1f}</text>'
            )
        label = html.escape(row["label"])
        elements.append(
            f'<text x="{cx:.2f}" y="{height-bottom+30}" transform="rotate(-25 {cx:.2f},{height-bottom+30})" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#222">{label}</text>'
        )

    legend_x = left + 12
    legend_y = top + 18
    for index, (label, color) in enumerate(
        (("Router A -> mobile", COLORS["router_a_to_mobile"]), ("mobile -> current parent", COLORS["mobile_to_parent"]))
    ):
        y = legend_y + index * 20
        elements.append(f'<rect x="{legend_x}" y="{y-10}" width="18" height="12" fill="{color}"/>')
        elements.append(f'<text x="{legend_x+26}" y="{y}" font-family="Arial, sans-serif" font-size="12">{label}</text>')

    elements.append("</svg>")
    write_svg(output, "\n".join(elements) + "\n")


def main() -> int:
    args = parse_args()
    if args.command == "run":
        plot_run(args.csv_file, args.output, args.title)
    elif args.command == "matrix":
        plot_matrix(args.artifacts, args.output, args.title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
