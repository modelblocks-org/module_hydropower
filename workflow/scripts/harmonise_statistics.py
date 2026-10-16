"""Extract annual hydropower generation for all EIA countries and territories."""

import io
import logging
import sys
import zipfile
from typing import TYPE_CHECKING, Any

import _schemas
import country_converter as coco
import pandas as pd

if TYPE_CHECKING:
    snakemake: Any

CAT_ID = {
    "hydropower": 33
    # "pumped storage": 82, TODO: add pumped storage estimations in future updates
}


def log_unrecognised_codes(statistics: pd.DataFrame) -> None:
    """Log codes that CoCo cannot identify."""
    codes = statistics["country_id"].drop_duplicates()
    converter = coco.CountryConverter()
    unrecognised = sorted(codes[~codes.isin(converter.data["ISO3"])])
    logging.info(
        "coco does not recognise %d of %d country codes: %s",
        len(unrecognised),
        len(codes),
        ", ".join(unrecognised) if unrecognised else "none",
    )


def harmonise(input_eia_bulk: str, output_generation: str):
    """Extract all available years, retaining EIA country codes and missing values."""
    with zipfile.ZipFile(input_eia_bulk) as zf:
        with zf.open("INTL.txt") as f:
            eia_stats = pd.read_json(io.TextIOWrapper(f, encoding="utf-8"), lines=True)

    results = []
    for category, identifier in CAT_ID.items():
        series = eia_stats[
            eia_stats["series_id"].str.fullmatch(
                rf"INTL\.{identifier}-12-.+-BKWH\.A", na=False
            )
        ].copy()
        series["country_id"] = series["series_id"].str.split("-").str[2]
        # Aggregates and alternative series have a different country_id and geography.
        # We force match to retain only countries, historical bodies and non-ISO territories.
        series = series[series["country_id"] == series["geography"]]

        for country in series.itertuples():
            data = pd.DataFrame(country.data, columns=["year", "generation_mwh"])
            values = data["generation_mwh"]
            data["generation_mwh"] = (
                pd.to_numeric(
                    values.mask(values.isin(["--", "ie", "NA"])), errors="raise"
                )
                * 1e6
            )  # EIA data is in billion kWh.
            data["country_id"] = country.country_id
            data["category"] = category
            results.append(data)

    statistics = _schemas.EIAGenerationSchema.validate(
        pd.concat(results, ignore_index=True)
    )
    log_unrecognised_codes(statistics)
    statistics.to_parquet(output_generation)


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    logging.basicConfig(level=logging.INFO)
    harmonise(
        input_eia_bulk=snakemake.input.eia_bulk,
        output_generation=snakemake.output.generation,
    )
