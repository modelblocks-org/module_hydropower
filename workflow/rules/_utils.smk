"""Utility functions for the module."""

from snakemake.io import apply_wildcards


def prefer_existing(file_path):
    """Prevents re-downloads even in forced cases.

    Useful for protecting invariable files.
    """

    def resolve_output(wildcards):
        path = apply_wildcards(str(file_path), wildcards)
        return before_update(path) if exists(path) else path

    return resolve_output


def validate_year_config():
    start = config["years"]["start"]
    end = config["years"]["end"]
    if not start < end:
        raise ValueError(
            f"Start year must be less than end year. Found: '{start},{end}'. "
            "Remember: end year data is not included!"
        )


def get_generation_adjustement_file() -> str:
    """Identify which generation adjustment file to use."""
    source = config["powerplants"]["generation_adjustement"]
    match source:
        case "EIA":
            return "<statistics_eia>"
        case "user":
            return "<statistics_user>"
        case _:
            raise ValueError(f"Invalid generation adjustment option {source}")
