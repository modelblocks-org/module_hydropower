"""Download GloFAS historical river discharge for the area of the shapes."""

import logging
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cdsapi
import geopandas as gpd
import xarray as xr

if TYPE_CHECKING:
    snakemake: Any


def download_area(shapes_file: str, crs: str, padding_deg: float) -> list[float]:
    """Bounding box of the shapes, padded, as [north, west, south, east]."""
    west, south, east, north = gpd.read_parquet(shapes_file).to_crs(crs).total_bounds
    return [
        min(north + padding_deg, 90.0),
        max(west - padding_deg, -180.0),
        max(south - padding_deg, -90.0),
        min(east + padding_deg, 180.0),
    ]


def glofas_request(year: int, area: list[float], system_version: str) -> dict:
    """EWDS request for one year of daily mean discharge (request schema as of July 2026)."""
    return {
        "system_version": [system_version],
        "hydrological_model": ["lisflood"],
        "product_type": ["consolidated"],
        "timespan": ["time_mean"],
        "variable": ["average_river_discharge_in_the_last_24_hours"],
        "year": [str(year)],
        "month": [f"{m:02d}" for m in range(1, 13)],
        "day": [f"{d:02d}" for d in range(1, 32)],
        "area": area,
        "data_format": "netcdf",
        "download_format": "unarchived",
    }


def download_glofas_discharge(
    shapes_file: str,
    start_year: int,
    end_year: int,
    settings: dict,
    padding_deg: float,
    crs: str,
    output_file: str,
):
    """Download daily GloFAS discharge [m3/s] for [start_year, end_year), one request per year.

    The EWDS url is set explicitly, so ~/.cdsapirc may keep pointing to the Climate Data Store
    for ERA5; the API key is read from ~/.cdsapirc or from CDSAPI_KEY.
    """
    area = download_area(shapes_file, crs, padding_deg)
    logging.info("GloFAS download area [N, W, S, E]: %s", area)
    client = cdsapi.Client(url=settings["ewds_url"])

    with tempfile.TemporaryDirectory() as tmp:
        yearly = []
        for year in range(start_year, end_year):
            target = Path(tmp) / f"glofas_{year}.nc"
            request = glofas_request(year, area, settings["system_version"])
            logging.info("Requesting %s for %d", settings["dataset"], year)
            client.retrieve(settings["dataset"], request, str(target))
            yearly.append(xr.open_dataset(target))
        discharge = xr.concat(yearly, dim="valid_time").sortby("valid_time")
        discharge.attrs["glofas_system_version"] = settings["system_version"]
        discharge.to_netcdf(output_file)
        for ds in yearly:
            ds.close()


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    download_glofas_discharge(
        shapes_file=snakemake.input.shapes,
        start_year=snakemake.params.start_year,
        end_year=snakemake.params.end_year,
        settings=snakemake.params.settings,
        padding_deg=snakemake.params.padding_deg,
        crs=snakemake.params.crs,
        output_file=snakemake.output.discharge,
    )
