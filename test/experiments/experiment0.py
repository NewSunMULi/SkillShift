"""实验 0：验证概率真值与适用域变化。 / Experiment 0: validate truth and domain transitions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..environment import PHASE_NAMES
from ..common.reporting import write_domain_report
from ..rover import SKILL_NAMES
from ..rover.simulator import MarsReliabilitySimulator


def _domains(sim: MarsReliabilitySimulator) -> dict[int, dict[str, set[str]]]:
    """计算各阶段每项技能的真实适用域。 / Compute true skill domains for every phase."""
    return {
        phase: {
            skill: {c.id for c in sim.contexts if sim.is_applicable(phase, skill, c)}
            for skill in SKILL_NAMES
        }
        for phase in range(1, 7)
    }


def run_experiment(seed: int = 20260927) -> dict:
    """运行可复现实验并返回内存报告。 / Run the reproducible experiment and return its report."""
    sim = MarsReliabilitySimulator(seed)
    domains = _domains(sim)
    total = len(sim.contexts)
    rows = []
    for phase in range(1, 7):
        for skill in SKILL_NAMES:
            current = domains[phase][skill]
            previous = domains[phase - 1][skill] if phase > 1 else current
            failed, gained = previous - current, current - previous
            recovered = (domains[1][skill] - previous) & current if phase > 1 else set()
            rows.append({
                "phase": phase, "phase_name": PHASE_NAMES[phase - 1], "skill": skill,
                "mu_U": len(current) / total, "mu_F": len(failed) / total,
                "mu_G": len(gained) / total, "mu_Rec_from_1": len(recovered) / total,
            })

    checks = {
        "300_standard_contexts": total == 300 and len({c.id for c in sim.contexts}) == 300,
        "100_distinct_generalization_contexts": len(sim.generalization_contexts) == 100
            and not ({c.id for c in sim.contexts} & {c.id for c in sim.generalization_contexts}),
        "phase4_exactly_recovers_phase1": domains[4] == domains[1],
        "phase2_only_changes_communication": all(
            domains[2][s] == domains[1][s] for s in SKILL_NAMES if s != "communicate"
        ) and bool(domains[1]["communicate"] - domains[2]["communicate"]),
        "phase3_has_local_heater_failure": bool(domains[2]["heat"] - domains[3]["heat"])
            and domains[3]["move"] == domains[1]["move"],
        "phase5_has_local_camera_failure": bool(domains[4]["image"] - domains[5]["image"])
            and domains[5]["move"] == domains[1]["move"],
        "phase6_replays_phase3_applicability": domains[6] == domains[3],
        "seed_reproduces_logs": sim.sample_logs(2, 30) == MarsReliabilitySimulator(seed).sample_logs(2, 30),
    }
    if not all(checks.values()):
        raise AssertionError({name: ok for name, ok in checks.items() if not ok})
    return {"seed": seed, "checks": checks, "metrics": rows}


def main() -> None:
    """解析命令行参数并写出实验报告。 / Parse CLI arguments and write the experiment report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260927)
    parser.add_argument("--output", type=Path, default=Path("test/results/experiment0"))
    args = parser.parse_args()
    report = run_experiment(args.seed)
    write_domain_report(report, args.output)
    print(json.dumps(report["checks"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
