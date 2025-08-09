"""Calculate the water inflow of relevant powerplants."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import _schemas
import atlite
import geopandas as gpd

if TYPE_CHECKING:
    snakemake: Any
sys.stderr = open(snakemake.log[0], "w", buffering=1)


def powerplants_get_inflow_m3(
    shapes_file: Path,
    powerplants_file: Path,
    basins_file: Path,
    cutout_file: Path,
    smoothing_hours: str,
    inflow_file: Path,
):
    """Get powerplant inflow using 'atlite'.

    Args:
        shapes_file (Path): user shapes.
        powerplants_file (Path): adjusted powerplants file.
        basins_file (Path): global basins file.
        cutout_file (Path): atlite cutout fitting the user shape.
        smoothing_hours (str): smoothing hours in the form '1h'.
        inflow_file (Path): resulting water inflow per powerplant.
    """
    basins = gpd.read_parquet(basins_file)
    powerplants = gpd.read_parquet(powerplants_file)
    powerplants = _schemas.PowerplantSchema.validate(powerplants)
    shapes = gpd.read_parquet(shapes_file)
    shapes = _schemas.ShapeSchema.validate(shapes)

    cutout = atlite.Cutout(path=cutout_file)
    era5_crs = cutout.crs

    # atlite does not support CRS conversion, adapt data to it instead
    assert era5_crs.is_geographic
    shapes = shapes.to_crs(era5_crs)
    powerplants = powerplants.to_crs(era5_crs)
    basins = basins.to_crs(era5_crs)

    # Re-format for atlite
    powerplants["lon"] = powerplants.geometry.apply(lambda point: point.x)
    powerplants["lat"] = powerplants.geometry.apply(lambda point: point.y)
    powerplants = powerplants.drop("geometry", axis="columns").set_index(
        "powerplant_id"
    )
    # Calculate inflow
    inflow = cutout.hydro(plants=powerplants, hydrobasins=basins)
    inflow = inflow.rename(plant="powerplant_id")
    inflow_df = inflow.to_pandas().T

    # Smoothen the timeseries to shave peaks and re-scale to the original magnitude
    inflow_smooth = inflow_df.rolling(window=smoothing_hours, min_periods=1).mean()
    inflow_df = (inflow_smooth / inflow_smooth.sum()) * inflow_df.sum()

    inflow_df.attrs = {"long_name": "Water inflow", "units": "cubic_meter"}
    inflow_df.to_parquet(inflow_file)


if __name__ == "__main__":
    powerplants_get_inflow_m3(
        shapes_file=snakemake.input.shapes,
        powerplants_file=snakemake.input.adjusted_powerplants,
        basins_file=snakemake.input.basins,
        cutout_file=snakemake.input.cutout,
        smoothing_hours=snakemake.params.smoothing_hours,
        inflow_file=snakemake.output.inflow,
    )
