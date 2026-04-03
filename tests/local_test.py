"""A collection of heavier tests to run locally.

Useful for debugging or testing new features.

Important things to consider:
 - These tests should be run individually to avoid excessive workloads.
 - Should only be run locally, as they are likely too heavy for Github's CI.
"""

import subprocess
from pathlib import Path

import pytest

TECHNOLOGIES = ["reservoir", "run_of_river"]


def build_request(case: str):
    """Construct a request for the given case."""
    return " ".join(
        [f"results/{case}/aggregated/{tech}_inflow_pu.parquet" for tech in TECHNOLOGIES]
    )


@pytest.mark.parametrize("case", ["MEX", "MNE", "europe"])
def test_full_run(user_path: Path, case: str):
    """Test a full request of categories a given setup can give.

    NNN-aggregated-adjusted is often the most holistic case.
    """
    request = build_request(case)

    assert subprocess.run(
        f"snakemake --use-conda --cores 4 --forceall {request}",
        shell=True,
        check=True,
        cwd=user_path.parent.parent,
    )
    assert subprocess.run(
        f"snakemake --use-conda --cores 4 {request} --report results/{case}/report.html",
        shell=True,
        check=True,
        cwd=user_path.parent.parent,
    )
    assert subprocess.run(
        f"snakemake --use-conda --cores 4 {request} --rulegraph | dot -Tpng > results/{case}/rulegraph.png",
        shell=True,
        check=True,
        cwd=user_path.parent.parent,
    )
