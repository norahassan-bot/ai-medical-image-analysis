#!/usr/bin/env python3
"""CLI utility for Prescription Dataset Acquisition, Synthesis, and Validation.

Usage:
    python backend/scripts/prescription_dataset_manager.py --build
    python backend/scripts/prescription_dataset_manager.py --validate
    python backend/scripts/prescription_dataset_manager.py --report
"""

import sys
import argparse
import json
from pathlib import Path

# Ensure backend/src is on python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from prescriptions.dataset_manager import PrescriptionDatasetManager


def main():
    parser = argparse.ArgumentParser(description="Prescription Dataset Manager CLI")
    parser.add_argument("--build", action="store_true", help="Generate sample dataset artifacts & metadata")
    parser.add_argument("--validate", action="store_true", help="Perform integrity, leakage, and corruption checks")
    parser.add_argument("--catalog", action="store_true", help="Display dataset catalog summary")

    args = parser.parse_args()
    manager = PrescriptionDatasetManager()

    if args.build or len(sys.argv) == 1:
        print("\n[+] Initializing directories and saving catalog metadata...")
        manager.save_catalog_metadata()
        print("[+] Building sample prescription datasets and benchmark records...")
        counts = manager.build_synthetic_and_sample_data()
        print(f"    - Generated samples: {counts}")

    if args.validate or len(sys.argv) == 1:
        print("\n[+] Running Prescription Dataset Integrity Audit...")
        summary = manager.verify_dataset_integrity()
        print(json.dumps(summary, indent=2))
        if summary["quality_gate_passed"]:
            print("\n[SUCCESS] Quality gate passed: 0 corrupted files, valid splits, zero leakage.")
        else:
            print("\n[FAIL] Quality gate issues detected!")
            sys.exit(1)

    if args.catalog:
        catalog = manager.get_dataset_catalog()
        print(json.dumps(catalog, indent=2))


if __name__ == "__main__":
    main()
