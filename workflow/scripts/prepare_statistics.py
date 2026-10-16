"""Aggregated hydropower generation data at a country level."""

import logging
import sys
from typing import TYPE_CHECKING, Any

import _plots
import _schemas
import geopandas as gpd
import pandas as pd
from matplotlib import pyplot as plt

if TYPE_CHECKING:
    snakemake: Any


def prepare(input_shapes: str, input_statistics: str, output_generation: str):
    """Select all available annual statistics for the countries in the shapes.

    Args:
        input_shapes (str): shapes parquet file.
        input_statistics (str): Harmonised EIA generation parquet file.
        output_generation (str): hydropower generation parquet file.
    """
    shapes = gpd.read_parquet(input_shapes)
    shapes = _schemas.ShapeSchema.validate(shapes)

    statistics = _schemas.EIAGenerationSchema.validate(
        pd.read_parquet(input_statistics)
    )
    countries = shapes["country_id"].unique()
    missing_countries = sorted(set(countries).difference(statistics["country_id"]))
    if missing_countries:
        raise ValueError(
            f"Missing generation statistics for countries: {missing_countries}"
        )
    statistics = statistics[statistics["country_id"].isin(countries)].reset_index(
        drop=True
    )

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

            pivot = cats.pivot(
                index="year", columns="category", values="generation_mwh"
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
    logging.basicConfig(level=logging.INFO)
    prepare(
        input_shapes=snakemake.input.shapes,
        input_statistics=snakemake.input.statistics,
        output_generation=snakemake.output.generation,
    )
    plot(
        input_generation=snakemake.output.generation, output_plot=snakemake.output.plot
    )
