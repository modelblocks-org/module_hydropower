"""Utility functions for the module."""


def validate_year_config():
    start = config["years"]["start"]
    end = config["years"]["end"]
    if not start < end:
        raise ValueError(
            f"Start year must be less than end year. Found: '{start},{end}'. "
            "Remember: end year data is not included!"
        )
