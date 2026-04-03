"""Transform from HydroBASINS zipped files to parquet."""

import sys
from typing import TYPE_CHECKING, Any

import geopandas as gpd

if TYPE_CHECKING:
    snakemake: Any
sys.stderr = open(snakemake.log[0], "w", buffering=1)
SHP_ZIP_PATH = "hybas_{continent}_lev{level}_v1c.shp"


# ---
# Taken from Euro-Calliope (MIT licensed)s
# https://github.com/calliope-project/euro-calliope/blob/c48f0c40f0f984772c484aa154002c68d027a7c6/scripts/hydro/preprocess_basins.py
def _buffer_if_necessary(shape):
    """Fix the basins shapes which are invalid.

    Following the advice given here:
    https://github.com/Toblerity/Shapely/issues/344
    """
    if not shape.is_valid:
        shape = shape.buffer(0.0)
    assert shape.is_valid
    return shape


# ---
def basins_extract_pfafstetter_level(zip_file, continent, level, parquet_file):
    """Extract a specific pfafstetter level from a HydroBASINS zip file."""
    inner_path = SHP_ZIP_PATH.format(continent=continent, level=level)
    gdf = gpd.read_file(f"{zip_file}!{inner_path}")
    gdf["geometry"] = gdf["geometry"].map(_buffer_if_necessary)
    gdf.to_parquet(parquet_file)


if __name__ == "__main__":
    basins_extract_pfafstetter_level(
        zip_file=snakemake.input.zip_file,
        continent=snakemake.params.continent,
        level=snakemake.params.level,
        parquet_file=snakemake.output.parquet_file,
    )
