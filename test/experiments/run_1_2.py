"""Run experiments 1 and 2 from one shared model-assessment session."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..common.reporting import write_json_with_tables
from ..evaluation.dify import DifyWorkflowConfig
from ..evaluation.session import build_session
from .experiment1 import run_experiment as run_experiment1
from .experiment2 import run_experiment as run_experiment2


def run_experiments(
    *, system_name: str = "id-baseline", seed: int = 20260927, eta: float = 0.1,
    dify_config: DifyWorkflowConfig | None = None, memory_log_limit: int = 2000,
) -> dict[str, object]:
    session = build_session(
        system_name=system_name, seed=seed, eta=eta, dify_config=dify_config,
        memory_log_limit=memory_log_limit,
    )
    return {
        "configuration": session.configuration,
        "invalid_outputs": list(session.run.invalid_outputs),
        "experiment1": run_experiment1(session, eta=eta),
        "experiment2": run_experiment2(session, eta=eta),
    }


def write_experiment_report(report: dict[str, object], output: Path) -> None:
    write_json_with_tables(
        report, output,
        {
            "experiment1_rows.csv": report["experiment1"]["rows"],  # type: ignore[index]
            "experiment2_rows.csv": report["experiment2"]["rows"],  # type: ignore[index]
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", choices=("id-baseline", "oracle", "dify"), default="id-baseline")
    parser.add_argument("--seed", type=int, default=20260927)
    parser.add_argument("--eta", type=float, default=0.1)
    parser.add_argument("--memory-log-limit", type=int, default=2000)
    parser.add_argument("--output", type=Path, default=Path("test/results/experiments_1_2"))
    args = parser.parse_args()
    report = run_experiments(
        system_name=args.system, seed=args.seed, eta=args.eta, memory_log_limit=args.memory_log_limit,
    )
    write_experiment_report(report, args.output)
    print(json.dumps({
        "experiment1": report["experiment1"]["summary"],  # type: ignore[index]
        "experiment2": report["experiment2"]["summary"],  # type: ignore[index]
        "invalid_outputs": len(report["invalid_outputs"]),  # type: ignore[arg-type]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
