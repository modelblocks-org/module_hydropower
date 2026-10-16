"""Shared test fixtures."""

import os
import shutil
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

import pytest

TEST_FILES = "https://zenodo.org/records/19401947/files/test_suite.zip?download=1"


def dir_to_dir_copy(source_dir: Path, target_dir: Path) -> None:
    """Copy all files from one directory into another."""
    target_dir.mkdir(parents=True, exist_ok=True)
    for file in source_dir.iterdir():
        if file.is_file():
            shutil.copy(file, target_dir / file.name)


@pytest.fixture(scope="session")
def cds_api_file() -> Path:
    """Ensure the CDS API file is present in the system."""
    cds_file = Path.home().joinpath(".cdsapirc")

    if not cds_file.exists():
        cdsapi_key = os.getenv("CDSAPI_KEY")

        if cdsapi_key:
            cds_file.write_text(
                f"url: https://cds.climate.copernicus.eu/api\nkey: {cdsapi_key}\n"
            )
        else:
            raise RuntimeError("Neither CDSAPI_KEY or the CDS API file is present.")

    return cds_file


@pytest.fixture(scope="session")
def user_path(cds_api_file) -> Path:
    """Download and unzip test files."""
    user_dir = Path("resources/user/")
    # If test suite has been downloaded, assume everything is OK.
    # Otherwise, cleanup and re-download.
    if not Path(user_dir / "test_suite.zip").exists():
        shutil.rmtree(user_dir, ignore_errors=True)
        Path(user_dir).mkdir(parents=True, exist_ok=True)
        test_zip = Path(user_dir / "test_suite.zip")
        urlretrieve(TEST_FILES, test_zip)
        with zipfile.ZipFile(test_zip, "r") as zfile:
            zfile.extractall(user_dir)
    return user_dir


@pytest.fixture(scope="module")
def module_path(cds_api_file: Path):
    """Parent directory of the project."""
    module_path = Path(__file__).parent.parent

    integration_dir = Path(module_path / "tests/integration")

    # clean files produced by the integration test
    if integration_dir.exists():
        shutil.rmtree(integration_dir / "resources/", ignore_errors=True)
        shutil.rmtree(integration_dir / "results/", ignore_errors=True)

    # copy user inputs needed by the module
    dir_to_dir_copy(
        module_path / "tests/files/MNE", integration_dir / "resources/inputs/MNE"
    )
    # copy downloads with unstable Github CI access
    dir_to_dir_copy(
        module_path / "tests/files/hydrobasins",
        integration_dir / "resources/module/resources/automatic/hydrobasins",
    )

    return module_path
