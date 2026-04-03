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
    input_generation: str,
    output_plot: str,
    *,
    min_fig_width: float = 5,
    width_per_year: float = 0.35,
    row_height: float = 3.0,
    base_height: float = 0.8,
    x_tick_rotation: float = 45,
    legend_anchor_x: float = 1.02,
):
    """Plot per-country evolution of hydropower generation over time."""
    df_cats = pd.read_parquet(input_generation)

    countries = sorted(df_cats["country_id"].dropna().unique())
    years = sorted(df_cats["year"].dropna().unique())

    n_countries = max(1, len(countries))
    n_years = max(1, len(years))

    fig_width = max(min_fig_width, width_per_year * n_years)
    fig_height = base_height + row_height * n_countries

    fig, axes = plt.subplots(
        nrows=n_countries,
        ncols=1,
        figsize=(fig_width, fig_height),
        squeeze=False,
        layout="constrained",
    )
    axes = axes.ravel()

    if not countries:
        _plots.draw_empty(axes[0], "No countries")
    else:
        for ax, country in zip(axes, countries):
            cats = df_cats[df_cats["country_id"] == country]

            if cats.empty:
                _plots.draw_empty(ax, str(country))
                continue

            pivot = cats.pivot_table(
                index="year",
                columns="category",
                values="generation_mwh",
                aggfunc="sum",
                fill_value=0,
            ).sort_index()

            pivot.plot.bar(ax=ax, stacked=True, legend=False, zorder=1)

            handles, labels = ax.get_legend_handles_labels()
            ax.legend(
                handles[::-1],
                labels[::-1],
                title="Category",
                bbox_to_anchor=(legend_anchor_x, 0.5),
                loc="center left",
                borderaxespad=0,
            )

            ax.tick_params(axis="x", labelrotation=x_tick_rotation)
            ax.set_title(str(country), fontweight="bold")
            ax.set_ylabel(r"Generation ($MWh$)")
            ax.set_xlabel("Year")

    fig.savefig(output_plot, bbox_inches="tight", pad_inches="layout")
    plt.close(fig)


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    prepare(
        input_shapes=snakemake.input.shapes,
        input_eia_bulk=snakemake.input.eia_bulk,
        years=snakemake.params.years,
        output_generation=snakemake.output.generation,
    )
    plot(
        input_generation=snakemake.output.generation, output_plot=snakemake.output.plot
    )
