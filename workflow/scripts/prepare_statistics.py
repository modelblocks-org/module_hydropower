"""Aggregated hydropower generation data at a country level."""

import sys
from typing import TYPE_CHECKING, Any

import _plots
import _schemas
import geopandas as gpd
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator

if TYPE_CHECKING:
    snakemake: Any
sys.stderr = open(snakemake.log[0], "w", buffering=1)

CAT_ID = {
    "hydropower": 33
    # "pumped storage": 82, TODO: add pumped storage estimations in future updates
}


def _get_id_data(eia_df: pd.DataFrame, code: str) -> pd.DataFrame:
    idx = eia_df[eia_df["series_id"] == code].index[0]
    df = pd.DataFrame(eia_df.loc[idx, "data"], columns=["year", "value"])
    df = df.replace("NA", np.nan)
    return df


def _get_generation_id_data(
    eia_df: pd.DataFrame, country_a3: str, category_id: int
) -> pd.DataFrame:
    """Returns annual generation in Billion KWh."""
    code = f"INTL.{category_id}-12-{country_a3}-BKWH.A"
    return _get_id_data(eia_df, code)


def _get_country_hydro_generation(eia_df: pd.DataFrame, country_a3: str):
    """Parse country generation from the EIA dataset."""
    results = []
    for category, identifier in CAT_ID.items():
        data = _get_generation_id_data(eia_df, country_a3, identifier)
        data["category"] = category
        results.append(data)

    country_generation = pd.concat(results, ignore_index=True)
    country_generation.reset_index(drop=True)
    country_generation["generation_mwh"] = (
        pd.to_numeric(country_generation.pop("value"), errors="coerce") * 1e6
    )  # EIA data is in Billion kWh
    country_generation["country_id"] = country_a3
    return country_generation


def prepare(
    input_shapes: str, input_eia_bulk: str, years: dict, output_generation: str
):
    """Generate a file with annual hydropower generation statistics per country.

    Args:
        input_shapes (str): shapes parquet file.
        input_eia_bulk (str): eia bulk txt database.
        years (dict): dictionary with start/end years.
        output_generation (str): hydropower generation parquet file.
    """
    shapes = gpd.read_parquet(input_shapes)
    shapes = _schemas.ShapeSchema.validate(shapes)

    eia_stats = pd.read_json(input_eia_bulk, lines=True)

    results = []
    for country in shapes["country_id"].unique():
        try:
            results.append(_get_country_hydro_generation(eia_stats, country))
        except (ValueError, KeyError, IndexError) as ex:
            raise ValueError(f"Failed to extract statistics for {country}") from ex
    statistics = pd.concat(results, ignore_index=True).reset_index(drop=True)

    # Filter requested data and validate for completeness
    statistics["year"] = statistics["year"].astype(int)
    statistics = statistics[
        statistics["year"].isin(range(years["start"], years["end"]))
    ]
    statistics = _schemas.EIAGenerationSchema.validate(statistics)
    statistics.to_parquet(output_generation)


def plot(
    input_generation: str, output_plot: str, figsize: tuple[float, float] = (12, 6)
):
    """Plot per-country evolution of hydropower generation over time."""
    df_cats = pd.read_parquet(input_generation)

    countries = set(df_cats["country_id"].unique())
    n_countries = len(countries)

    fig, axes = plt.subplots(
        nrows=n_countries,
        ncols=1,
        figsize=(figsize[0], figsize[1] * n_countries),
        sharex=False,
        tight_layout=True,
    )
    if n_countries == 1:
        axes = [axes]

    for ax, country in zip(axes, sorted(countries)):
        cats = df_cats[df_cats["country_id"] == country]

        if cats.empty:
            _plots.draw_empty(ax, country)

        else:
            pivot = (
                cats.pivot_table(
                    index="year",
                    columns="category",
                    values="generation_mwh",
                    aggfunc="sum",
                )
                .fillna(0)
                .sort_index()
            )
            _ = pivot.plot(kind="bar", stacked=True, ax=ax, legend=False, zorder=1)

            handles, labels = ax.get_legend_handles_labels()
            ax.legend(
                handles[::-1],
                labels[::-1],
                title="Category",
                bbox_to_anchor=(1.02, 0.5),
                loc="center left",
                borderaxespad=0,
            )

            ax.xaxis.set_major_locator(MaxNLocator(nbins=10, integer=True))
            ax.tick_params(axis="x", rotation=45)
            ax.set_title(country)
            ax.set_ylabel("Generation ($MWh$)")
            ax.set_xlabel("Year")

    fig.savefig(output_plot, bbox_inches="tight")


if __name__ == "__main__":
    prepare(
        input_shapes=snakemake.input.shapes,
        input_eia_bulk=snakemake.input.eia_bulk,
        years=snakemake.params.years,
        output_generation=snakemake.output.generation,
    )
    plot(
        input_generation=snakemake.output.generation, output_plot=snakemake.output.plot
    )
