import argparse
import csv
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final

CSV_COLUMNS: Final = [
    "case_code",
    "stage_code",
    "activity",
    "timestamp",
    "resource",
    "event_type",
    "source",
    "metadata",
]
STAGE_NAMES: Final = {
    "LEAD": "Lead creado",
    "CONTACTED": "Lead contactado",
    "QUALIFIED": "Lead calificado",
    "VISIT": "Visita realizada",
    "RESERVED": "Separación registrada",
    "CONTRACT": "Minuta generada",
}
SCENARIOS: Final = {
    "NORMAL": ["LEAD", "CONTACTED", "QUALIFIED", "VISIT", "RESERVED", "CONTRACT"],
    "STAGE_SKIP": ["LEAD", "CONTACTED", "VISIT", "RESERVED"],
    "REWORK": ["LEAD", "CONTACTED", "QUALIFIED", "CONTACTED", "QUALIFIED", "VISIT"],
    "BACKTRACK": ["LEAD", "CONTACTED", "QUALIFIED", "VISIT", "QUALIFIED", "VISIT"],
    "LONG_DELAY": ["LEAD", "CONTACTED", "QUALIFIED", "VISIT"],
}
SCENARIO_WEIGHTS: Final = {
    "NORMAL": 55,
    "STAGE_SKIP": 10,
    "REWORK": 10,
    "BACKTRACK": 10,
    "LONG_DELAY": 15,
}
SOURCES: Final = ["META_ADS", "GOOGLE_ADS", "ORGANIC", "REFERRAL", "PORTAL"]
RESOURCES: Final = [f"Asesor {number:02d}" for number in range(1, 6)]
LIMA_TIMEZONE: Final = timezone(timedelta(hours=-5))


@dataclass(frozen=True, slots=True)
class GeneratedDataset:
    rows: list[dict[str, str]]
    ground_truth: list[dict[str, str]]


def generate_dataset(*, cases: int = 400, seed: int = 42) -> GeneratedDataset:
    if cases <= 0:
        raise ValueError("cases must be greater than zero")

    rng = random.Random(seed)
    scenario_names = list(SCENARIO_WEIGHTS)
    scenario_weights = list(SCENARIO_WEIGHTS.values())
    rows: list[dict[str, str]] = []
    ground_truth: list[dict[str, str]] = []
    base_time = datetime(2026, 1, 1, 8, 0, tzinfo=LIMA_TIMEZONE)

    for case_number in range(1, cases + 1):
        case_code = f"DEMO-{case_number:05d}"
        scenario = rng.choices(
            scenario_names,
            weights=scenario_weights,
            k=1,
        )[0]
        source = rng.choice(SOURCES)
        resource = rng.choice(RESOURCES)
        current_time = base_time + timedelta(
            days=rng.randint(0, 180),
            minutes=rng.randint(0, 600),
        )

        for position, stage_code in enumerate(SCENARIOS[scenario]):
            if position > 0:
                if scenario == "LONG_DELAY" and position == 1:
                    current_time += timedelta(hours=rng.randint(96, 240))
                else:
                    current_time += timedelta(hours=rng.randint(1, 72))

            metadata = {
                "channel": rng.choice(["web", "phone", "whatsapp", "email"]),
                "generated": True,
            }
            rows.append(
                {
                    "case_code": case_code,
                    "stage_code": stage_code,
                    "activity": STAGE_NAMES[stage_code],
                    "timestamp": current_time.isoformat(),
                    "resource": resource,
                    "event_type": "STAGE_CHANGE",
                    "source": source,
                    "metadata": json.dumps(
                        metadata,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                }
            )

        ground_truth.append({"case_code": case_code, "scenario": scenario})

    return GeneratedDataset(rows=rows, ground_truth=ground_truth)


def write_dataset(
    dataset: GeneratedDataset,
    *,
    output: Path,
    ground_truth_output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    ground_truth_output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=CSV_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(dataset.rows)

    with ground_truth_output.open("w", encoding="utf-8", newline="") as truth_file:
        writer = csv.DictWriter(
            truth_file,
            fieldnames=["case_code", "scenario"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(dataset.ground_truth)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera un Event Log comercial ficticio y reproducible.",
    )
    parser.add_argument("--cases", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/demo_event_log.csv"),
    )
    parser.add_argument("--ground-truth", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ground_truth_output = args.ground_truth or args.output.with_name(
        f"{args.output.stem}_ground_truth.csv"
    )
    dataset = generate_dataset(cases=args.cases, seed=args.seed)
    write_dataset(
        dataset,
        output=args.output,
        ground_truth_output=ground_truth_output,
    )
    print(f"Generated cases: {len(dataset.ground_truth)}")
    print(f"Generated events: {len(dataset.rows)}")
    print(f"Event Log: {args.output}")
    print(f"Ground truth: {ground_truth_output}")


if __name__ == "__main__":
    main()
