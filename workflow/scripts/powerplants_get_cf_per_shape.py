"""Capacity factor calculation for hydropower basin and run-of-river plants."""

import sys
from typing import TYPE_CHECKING, Any

import _schemas
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    snakemake: Any
sys.stderr = open(snakemake.log[0], "w")


def _plot_cf_per_shape(cf_file: str, plant_type: str, fig_path: str):
    data = pd.read_parquet(cf_file)
    if not data.empty:
        fig, axes = plt.subplots(
            len(data.columns), 1, figsize=(10, 1.5 * len(data.columns))
        )
        for count, shape_id in enumerate(data.columns):
            data[shape_id].plot(ax=axes[count])
            axes[count].set_title(shape_id)
            axes[count].set_xlabel("")
        fig.suptitle(f"Inflow capacity factors {plant_type}", fontsize="x-large")
        fig.tight_layout()
    else:
        # If no data, create an empty figure to avoid snakemake issues.
        plt.plot()
    plt.savefig(fig_path, bbox_inches="tight")


def _get_capacity_factors_timeseries(
    tech: str, powerplants: pd.DataFrame, inflow_mwh: pd.DataFrame
) -> pd.DataFrame:
    """Calculate capacity factor timeseries within a shape for a given technology.

    Args:
        tech (str): name of the powerplant technology.
        powerplants (pd.DataFrame): powerplant data file.
        inflow_mwh (pd.DataFrame): timeseries of energy inflow per powerplant.

    Returns:
        pd.DataFrame: capacity factor timeseries (row: timestep, column: shape_id).
    """
    tech_powerplants = powerplants[powerplants["technology"] == tech]
    group = tech_powerplants.groupby(["shape_id"])
    shape_net_cap = group["output_capacity_mw"].sum()
    shape_powerplants = group["powerplant_id"].apply(list)

    shape_ids = sorted(tech_powerplants.shape_id.unique())
    cf_timeseries = pd.DataFrame(np.nan, index=inflow_mwh.index, columns=shape_ids)
    for shape_id in shape_ids:
        cf_timeseries[shape_id] = (
            inflow_mwh[shape_powerplants[shape_id]].sum(axis="columns")
            / shape_net_cap[shape_id]
        )

    if cf_timeseries.isna().any().any():
        ValueError(
            f"Calculated capacity factor timeseries must not contain null values {tech}."
        )

    cf_timeseries.attrs = {
        "long_name": "Capacity factors",
        "units": None,
        "technology": tech,
    }
    return cf_timeseries


def powerplants_get_cf_per_shape(
    powerplants_file: gpd.GeoDataFrame,
    inflow_mwh_file: pd.DataFrame,
    plant_type: str,
    output_path: str,
):
    """Construct a capacity factor file for each type of hydro plant."""
    powerplants = gpd.read_parquet(powerplants_file)
    inflow_mwh = pd.read_parquet(inflow_mwh_file)

    _schemas.PowerplantSchema.validate(powerplants)

    cap_factors = _get_capacity_factors_timeseries(plant_type, powerplants, inflow_mwh)
    cap_factors.to_parquet(output_path)


def main():
    """Calculate CFs and obtain plots."""
    powerplants_get_cf_per_shape(
        powerplants_file=snakemake.input.adjusted_powerplants,
        inflow_mwh_file=snakemake.input.inflow_mwh,
        plant_type=snakemake.wildcards.plant_type,
        output_path=snakemake.output.timeseries,
    )
    _plot_cf_per_shape(
        cf_file=snakemake.output.timeseries,
        plant_type=snakemake.wildcards.plant_type,
        fig_path=snakemake.output.figure,
    )


if __name__ == "__main__":
    main()
