"""Per-unit inflow factor calculation for hydropower basin and run-of-river plants."""

import sys
from typing import TYPE_CHECKING, Any

import _plots
import _schemas
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    snakemake: Any


def _plot_pu_per_shape(cf_file: str, plant_type: str, fig_path: str):
    """Plot a time series for every shape."""
    data = pd.read_parquet(cf_file)

    n = max(1, len(data.columns))
    row_height = 1.6
    fig_height = max(3.0, 1.0 + n * row_height)

    fig, axes = plt.subplots(
        nrows=n, ncols=1, figsize=(10, fig_height), squeeze=False, layout="constrained"
    )
    axes = axes.ravel()

    fig.suptitle(f"Per-unit inflow factors {plant_type}", fontsize="x-large")

    if data.empty:
        _plots.draw_empty(axes[0], f"No per-unit inflow factors {plant_type}")
    else:
        for ax, shape_id in zip(axes, data.columns):
            series = data[shape_id].dropna()

            if series.empty:
                _plots.draw_empty(ax, str(shape_id))
            else:
                ax.plot(data.index, data[shape_id])
                ax.set_title(
                    str(shape_id), loc="left", fontsize="medium", fontweight="bold"
                )
                ax.margins(x=0)

            ax.set_xlabel("")

    fig.savefig(fig_path, bbox_inches="tight", pad_inches="layout")
    plt.close(fig)


def _get_pu_factor_timeseries(
    tech: str, powerplants: pd.DataFrame, inflow_mwh: pd.DataFrame
) -> pd.DataFrame:
    """Calculate per-unit factor timeseries within a shape for a given technology.

    Args:
        tech (str): name of the powerplant technology.
        powerplants (pd.DataFrame): powerplant data file.
        inflow_mwh (pd.DataFrame): timeseries of energy inflow per powerplant.

    Returns:
        pd.DataFrame: pu factor timeseries (row: timestep, column: shape_id).
    """
    tech_powerplants = powerplants[powerplants["technology"] == tech]
    group = tech_powerplants.groupby(["shape_id"])
    shape_net_cap = group["output_capacity_mw"].sum()
    shape_powerplants = group["powerplant_id"].apply(list)

    shape_ids = sorted(tech_powerplants.shape_id.unique())
    pu_timeseries = pd.DataFrame(np.nan, index=inflow_mwh.index, columns=shape_ids)
    for shape_id in shape_ids:
        pu_timeseries[shape_id] = (
            inflow_mwh[shape_powerplants[shape_id]].sum(axis="columns")
            / shape_net_cap[shape_id]
        )

    if pu_timeseries.isna().any().any():
        raise ValueError(
            f"Calculated per-unit factor timeseries must not contain null values {tech}."
        )

    pu_timeseries.attrs = {
        "long_name": "Per-unit factors",
        "units": None,
        "technology": tech,
    }
    return pu_timeseries


def powerplants_get_pu_per_shape(
    powerplants_file: gpd.GeoDataFrame,
    inflow_mwh_file: pd.DataFrame,
    plant_type: str,
    technology_mapping: dict,
    output_path: str,
):
    """Construct a per-unit factor file for each type of hydro plant."""
    powerplants = gpd.read_parquet(powerplants_file)
    inflow_mwh = pd.read_parquet(inflow_mwh_file)

    _schemas.PowerplantSchema.validate(powerplants)

    user_plant_name = technology_mapping[plant_type]
    cap_factors = _get_pu_factor_timeseries(user_plant_name, powerplants, inflow_mwh)
    cap_factors.to_parquet(output_path)


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    powerplants_get_pu_per_shape(
        powerplants_file=snakemake.input.adjusted_powerplants,
        inflow_mwh_file=snakemake.input.inflow_mwh,
        plant_type=snakemake.wildcards.plant_type,
        technology_mapping=snakemake.params.technology_mapping,
        output_path=snakemake.output.timeseries,
    )
    _plot_pu_per_shape(
        cf_file=snakemake.output.timeseries,
        plant_type=snakemake.wildcards.plant_type,
        fig_path=snakemake.output.figure,
    )
