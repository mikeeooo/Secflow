"""SecFlow command line: generate, validate, train, evaluate.

    python -m backend.cli generate   # both seeded datasets + manifests
    python -m backend.cli validate   # schema, counts, partitions, hashes, fingerprints
    python -m backend.cli train      # fit on train, map on calibration, select on validation
    python -m backend.cli evaluate   # one frozen evaluation on the final test period
"""

from __future__ import annotations

import argparse
import json
import sys

from config.settings import load_settings
from ml.policy import load_policy
from storage.dataset import cross_dataset_fingerprint_overlap, validate_dataset
from storage.generator import DEMO_SPEC, TRAINING_SPEC, generate_dataset


def cmd_generate(_: argparse.Namespace) -> int:
    settings = load_settings()
    for spec, path in ((TRAINING_SPEC, settings.training_dir), (DEMO_SPEC, settings.demo_dir)):
        manifest = generate_dataset(path, spec)
        counts = manifest["counts"]
        print(
            f"{spec.name}: {counts['requests']} requests, {counts['fraud']} fraud, "
            f"{counts['unusual_legitimate']} unusual-legitimate, {counts['security_events']} security events -> {path}"
        )
    return cmd_validate(_)


def cmd_validate(_: argparse.Namespace) -> int:
    settings = load_settings()
    problems = []
    for spec, path in ((TRAINING_SPEC, settings.training_dir), (DEMO_SPEC, settings.demo_dir)):
        found = validate_dataset(path, spec)
        problems += [f"{spec.name}: {p}" for p in found]
        print(f"{spec.name}: {'valid' if not found else f'{len(found)} problem(s)'}")
    overlap = cross_dataset_fingerprint_overlap(settings.training_dir, settings.demo_dir)
    print(f"cross-dataset duplicate fingerprints: {overlap}")
    if overlap:
        problems.append("duplicate request fingerprints across datasets")
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    return 1 if problems else 0


def cmd_train(_: argparse.Namespace) -> int:
    from ml.training import train_models

    settings = load_settings()
    report = train_models(settings.training_dir, settings.models_dir, load_policy(settings.policy_path))
    print(json.dumps(
        {
            "operating_point": report["operating_point"],
            "validation_component_average_precision": report["validation_component_average_precision"],
            "chosen": report["threshold_selection"]["chosen"],
            "training_seconds": report["training_seconds"],
        },
        indent=2,
    ))
    return 0


def cmd_evaluate(_: argparse.Namespace) -> int:
    from ml.evaluation import run_evaluation

    settings = load_settings()
    summary = run_evaluation(settings)
    print(json.dumps(summary["headline"], indent=2))
    print(f"Wrote {settings.artifacts_dir / 'evaluation.json'} and evaluation.md")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="secflow", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("generate", cmd_generate), ("validate", cmd_validate), ("train", cmd_train),
                          ("evaluate", cmd_evaluate)):
        commands.add_parser(name).set_defaults(handler=handler)
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
