#!/usr/bin/env python3
"""Standalone validation suite for Prescription Datasets.

Validates:
1. File counts and metadata schema integrity.
2. Image integrity and non-corruption.
3. Duplicate identification.
4. Train/test data leakage prevention.
5. Privacy de-identification compliance.
"""

import sys
from pathlib import Path

# Add backend/src to path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from prescriptions.dataset_manager import PrescriptionDatasetManager


def run_validation():
    print("=" * 60)
    print("TASK 22: PRESCRIPTION DATASET QUALITY GATE & INTEGRITY AUDIT")
    print("=" * 60)

    manager = PrescriptionDatasetManager()
    summary = manager.verify_dataset_integrity()

    print(f"Total Datasets Cataloged: {summary['total_datasets_cataloged']}")
    print(f"Datasets Identified:       {', '.join(summary['datasets'])}")
    print("\nDataset Sample Distribution:")
    for d_name, count in summary["sample_counts"].items():
        print(f"  • {d_name:<28}: {count} samples")

    print(f"\nCorrupted Files:           {summary['corrupted_files_count']}")
    print(f"Duplicate Clusters:        {summary['duplicate_clusters_count']}")
    print(f"Data Leakage Verification: {summary['data_leakage_status']}")
    print(f"Privacy/PII Compliance:    {summary['privacy_compliance']}")

    print("-" * 60)
    if summary["quality_gate_passed"]:
        print("RESULT: ALL PRESCRIPTION DATASET QUALITY GATES PASSED [OK]")
        print("=" * 60)
        return 0
    else:
        print("RESULT: QUALITY GATE FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(run_validation())
