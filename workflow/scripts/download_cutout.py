"""Get a cutout with runoff data."""

import sys
from typing import TYPE_CHECKING, Any

import atlite
import geopandas as gpd
import matplotlib.pyplot as plt
from pyproj import CRS
from shapely.geometry import box

if TYPE_CHECKING:
    snakemake: Any


def _plot_cutout(shapes_file: str, cutout_file: str, era5_crs: str, path: str):
    cutout = atlite.Cutout(cutout_file)
    shapes = gpd.read_parquet(shapes_file).to_crs(era5_crs)

    fig, ax = plt.subplots(layout="constrained")
    shapes.boundary.plot(ax=ax, color="black")
    gpd.GeoSeries([box(*cutout.bounds)], crs=era5_crs).boundary.plot(
        ax=ax, color="red", linewidth=1
    )

    ax.set(title="ERA5 cutout", xticks=[], yticks=[], xlabel="", ylabel="")
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches="layout")
    plt.close(fig)


def runoff_cutout(input_shapes, era5_crs, start_year, end_year, output_netcdf):
    """Download runoff data from ERA5."""
    # Run quick checks before executing the download
    assert CRS(era5_crs).is_geographic

    shapes = gpd.read_parquet(input_shapes)
    shapes = shapes.to_crs(era5_crs)
    bounds = shapes.total_bounds

    cutout = atlite.Cutout(
        path=output_netcdf,
        module=["era5"],
        x=slice(bounds[0], bounds[2]),
        y=slice(bounds[1], bounds[3]),
        time=slice(f"{start_year}-01-01", f"{end_year - 1}-12-31"),
    )
    cutout.prepare(features=["runoff"])
    assert cutout.crs == era5_crs


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    runoff_cutout(
        input_shapes=snakemake.input.shapes,
        era5_crs=snakemake.params.era5_crs,
        start_year=snakemake.params.start_year,
        end_year=snakemake.params.end_year,
        output_netcdf=snakemake.output.cutout,
    )
    _plot_cutout(
        shapes_file=snakemake.input.shapes,
        cutout_file=snakemake.output.cutout,
        era5_crs=snakemake.params.era5_crs,
        path=snakemake.output.plot,
    )
