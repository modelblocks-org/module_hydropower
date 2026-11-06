"""Calculate the water inflow of relevant powerplants from GloFAS river discharge."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import _schemas
import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

if TYPE_CHECKING:
    snakemake: Any

KM_PER_DEG = 111.2


def _river_cell_area(discharge: xr.DataArray, uparea_file: Path) -> xr.DataArray:
    """Upstream area [km2] on the discharge grid, NaN where GloFAS has no discharge."""
    uparea = xr.open_dataset(uparea_file)["uparea"]
    uparea = uparea.sel(
        latitude=discharge["latitude"],
        longitude=discharge["longitude"],
        method="nearest",
    )
    # Compare raw values: xarray arithmetic would align on labels that differ by ~1e-13
    mismatch = max(
        float(np.abs(uparea["latitude"].values - discharge["latitude"].values).max()),
        float(np.abs(uparea["longitude"].values - discharge["longitude"].values).max()),
    )
    if mismatch > 1e-6:
        raise ValueError(
            f"Upstream area and discharge grids are not aligned (max offset {mismatch} deg)."
        )
    uparea = uparea.assign_coords(
        latitude=discharge["latitude"], longitude=discharge["longitude"]
    )
    has_discharge = discharge.notnull().any("valid_time")
    return (uparea / 1e6).where(has_discharge)


def _pick_cells(
    plants: gpd.GeoDataFrame, area_km2: xr.DataArray, window: int
) -> pd.DataFrame:
    """For each powerplant, the cell with the largest upstream area within +-window cells.

    This is a simple approximation of the river location: it tends to pick the largest river
    near the plant, so a small plant on a tributary can be moved onto the main river.

    TODO: replace with a physically-based river snapping (see issue #26), e.g. a score
    combining distance and the match between the cell discharge and the plant design flow.
    """
    lats = area_km2["latitude"].to_numpy()
    lons = area_km2["longitude"].to_numpy()
    values = area_km2.to_numpy()
    rows, missing = [], []
    for plant_id, point in zip(plants["powerplant_id"], plants.geometry):
        i = int(np.abs(lats - point.y).argmin())
        j = int(np.abs(lons - point.x).argmin())
        i0, j0 = max(i - window, 0), max(j - window, 0)
        block = values[i0 : i + window + 1, j0 : j + window + 1]
        if not np.isfinite(block).any():
            missing.append(plant_id)
            continue
        bi, bj = np.unravel_index(np.nanargmax(block), block.shape)
        ci, cj = int(i0 + bi), int(j0 + bj)
        dy = (lats[ci] - point.y) * KM_PER_DEG
        dx = (lons[cj] - point.x) * KM_PER_DEG * np.cos(np.radians(point.y))
        rows.append(
            {
                "powerplant_id": plant_id,
                "i": ci,
                "j": cj,
                "lat": float(lats[ci]),
                "lon": float(lons[cj]),
                "uparea_km2": float(values[ci, cj]),
                "distance_km": float(np.hypot(dx, dy)),
            }
        )
    if missing:
        raise ValueError(
            f"No GloFAS river cell within the search window for: {missing}"
        )
    return pd.DataFrame(rows)


def _daily_to_hourly_m3(daily_m3s: pd.DataFrame) -> pd.DataFrame:
    """Daily mean discharge [m3/s] -> hourly volume [m3], linear between daily values at noon."""
    hours = pd.date_range(
        daily_m3s.index[0], daily_m3s.index[-1] + pd.Timedelta(hours=23), freq="h"
    )
    noon = daily_m3s.set_axis(daily_m3s.index + pd.Timedelta(hours=12))
    hourly = noon.reindex(hours).interpolate(method="time", limit_area="inside")
    return hourly.ffill().bfill() * 3600


def powerplants_get_inflow_m3_glofas(
    powerplants_file: Path,
    discharge_file: Path,
    uparea_file: Path,
    search_window_cells: int,
    inflow_file: Path,
    cells_file: Path,
):
    """Get powerplant inflow from the GloFAS discharge of the river cell next to each powerplant.

    Args:
        powerplants_file (Path): adjusted powerplants file.
        discharge_file (Path): GloFAS daily mean discharge for the shapes.
        uparea_file (Path): GloFAS upstream area on the same grid.
        search_window_cells (int): half-size of the square search window, in cells.
        inflow_file (Path): resulting water inflow per powerplant [m3 per hour].
        cells_file (Path): GloFAS cell chosen for each powerplant.
    """
    plants = _schemas.PowerplantSchema.validate(gpd.read_parquet(powerplants_file))
    plants = plants.to_crs("epsg:4326")

    discharge = xr.open_dataset(discharge_file)["avg_dis"]
    area_km2 = _river_cell_area(discharge, uparea_file)
    cells = _pick_cells(plants, area_km2, search_window_cells)
    cells.to_parquet(cells_file)

    series = discharge.isel(
        latitude=xr.DataArray(cells["i"].to_numpy(), dims="powerplant_id"),
        longitude=xr.DataArray(cells["j"].to_numpy(), dims="powerplant_id"),
    ).assign_coords(powerplant_id=cells["powerplant_id"].to_numpy())
    daily = series.to_pandas()  # rows: time, columns: powerplant_id
    # GloFAS stamps each value at the end of its 24 h window: shift to the day of flow
    daily.index = pd.DatetimeIndex(daily.index) - pd.Timedelta(days=1)
    if daily.isna().any().any():
        raise ValueError("GloFAS discharge has gaps at the chosen cells.")

    inflow_df = _daily_to_hourly_m3(daily.clip(lower=0))
    inflow_df.index.name = "time"
    inflow_df.columns.name = "powerplant_id"
    inflow_df.attrs = {"long_name": "Water inflow", "units": "cubic_meter"}
    inflow_df.to_parquet(inflow_file)


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    powerplants_get_inflow_m3_glofas(
        powerplants_file=snakemake.input.adjusted_powerplants,
        discharge_file=snakemake.input.discharge,
        uparea_file=snakemake.input.uparea,
        search_window_cells=snakemake.params.search_window_cells,
        inflow_file=snakemake.output.inflow,
        cells_file=snakemake.output.cells,
    )
