"""Obtain magnitude-adjusted energy inflows for each powerplant in MWh."""

import sys
from calendar import isleap
from typing import TYPE_CHECKING, Any

import _schemas
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.optimize import minimize

if TYPE_CHECKING:
    snakemake: Any
sys.stderr = open(snakemake.log[0], "w", buffering=1)


# ---
# Taken from Euro-Calliope (MIT licensed)
# https://github.com/calliope-project/euro-calliope/blob/e9cb908a5b4c6274148a16b59e5dd0b412aaf560/scripts/hydro/inflow_mwh.py
def _water_inflow_m3_to_mwh(inflow_m3: pd.Series, annual_generation: float, cap: float):
    def generation(scaling_factor):
        generation = inflow_m3 * scaling_factor
        generation[generation > cap] = cap
        return generation

    def residual(scaling_factor):
        return abs(generation(scaling_factor).sum() - annual_generation)

    x0 = annual_generation / inflow_m3.sum()
    res = minimize(residual, x0, method="nelder-mead", options={"xatol": 1e-10})
    assert res.success, print(res)
    assert res.fun < 1, print(res)  # error smaller than 1 MWh

    return generation(res.x)


# ---


def _estimate_bounded_powerplant_inflow(
    powerplants: pd.DataFrame,
    inflow_m3: pd.DataFrame,
    national_generation: pd.DataFrame,
    year: int,
    capacity_factor_range: dict,
) -> pd.DataFrame:
    """Obtain magnitude-corrected hydropower timeseries dataset for a given year.

    The inflow timeseries will be scaled utilising national generation data.
    The aim is to correct its magnitude while retaining its dynamics.

    A capacity factor range is used to determine the upper limit and zero-cutoff.

    General assumptions:
        - Annual total never exceeds installed capacity * upper limit.
        - Values lower than the min. capacity factor range will be set to zero.
    """
    inflow_m3_yr = inflow_m3[inflow_m3.index.year == year]
    generation_yr = national_generation[national_generation.year == year]
    plants_by_id = powerplants.set_index("powerplant_id")

    # Re-scale capacity share to account for erroneous zero timesteps in the inflow data
    # TODO: accurately describe the reasoning behind this
    scaling_factor = inflow_m3_yr.where(inflow_m3_yr > 1).count(
        axis="index"
    ) / inflow_m3_yr.count(axis="index")

    national_cap_share_per_powerplant = (
        plants_by_id["output_capacity_mw"]
        .multiply(scaling_factor, axis="index")
        .groupby(plants_by_id["country_id"])
        .transform(lambda x: x / x.sum())
    )

    annual_national_generation = generation_yr.set_index("country_id")["generation_mwh"]
    assert annual_national_generation.index.is_unique, (
        f"Country data for {year} is not unique!"
    )

    annual_powerplant_mwh = plants_by_id.apply(
        lambda x: annual_national_generation[x.country_id]
        * national_cap_share_per_powerplant[x.name],
        axis="columns",
    )
    hours_in_year = 366 * 24 if isleap(year) else 365 * 24
    inflow_mwh_yr = pd.DataFrame(
        np.nan, index=inflow_m3_yr.index, columns=inflow_m3_yr.columns
    )

    for plant_id, plant_data in plants_by_id.iterrows():
        inflow_m3_per_hour = inflow_m3_yr[plant_id]
        annual_generation_mwh = annual_powerplant_mwh[plant_id]
        cf_range = capacity_factor_range[plant_data["technology"]]

        # Obtain MWh, ensuring max-cutoff is not exceeded
        max_cutoff = plant_data["output_capacity_mw"] * cf_range["max"]
        max_generation_mwh = max_cutoff * hours_in_year
        if annual_generation_mwh > max_generation_mwh:
            raise ValueError(
                f"{plant_id}: annual generation ({annual_generation_mwh}) exceeds the maximum ({max_generation_mwh})."
            )
        inflow_mwh_yr[plant_id] = _water_inflow_m3_to_mwh(
            inflow_m3_per_hour, annual_generation_mwh, max_cutoff
        )

        # Convert values below the minimum range to zero, to avoid very small numbers
        zero_cutoff = plant_data["output_capacity_mw"] * cf_range["min"]
        inflow_mwh_yr[plant_id] = inflow_mwh_yr[plant_id].where(
            inflow_mwh_yr[plant_id] >= zero_cutoff, 0
        )

    return inflow_mwh_yr


def powerplants_get_inflow_mwh(
    inflow_m3_file: str,
    powerplants_file: str,
    statistics_file: str,
    capacity_factor_range: dict,
    technology_mapping: dict,
    inflow_mwh_file: str,
):
    """Generate inflow timeseries using unscaled water time series.

    Args:
        inflow_m3_file (str): Dataset with water inflow per-powerplant in m3.
        powerplants_file (str): Powerplants dataset (adjusted).
        statistics_file (str): Annual national hydropower generation per country.
        capacity_factor_range (dict): Max/min range of inflow in relation to the plant's capacity.
        technology_mapping (dict): names of technologies in user files.
        inflow_mwh_file (str): Resulting file with energy inflow per powerplant in MWh.
    """
    inflow_m3 = pd.read_parquet(inflow_m3_file)
    generation = _schemas.EIAGenerationSchema.validate(pd.read_parquet(statistics_file))
    # Powerplants are only soft-validated to avoid filtering out imputed country IDs
    powerplants = gpd.read_parquet(powerplants_file)
    _schemas.PowerplantSchema.validate(powerplants)

    # Make our internal naming match the user's
    remapped_cf_range = {
        v: capacity_factor_range[k] for k, v in technology_mapping.items()
    }

    year_results = []
    for year in sorted(inflow_m3.index.year.unique()):
        inflow_mwh_yr = _estimate_bounded_powerplant_inflow(
            powerplants, inflow_m3, generation, year, remapped_cf_range
        )
        year_results.append(inflow_mwh_yr)

    inflow_mwh = pd.concat(year_results)
    inflow_mwh.attrs = {"long_name": "Energy inflow", "units": "Megawatt hour"}
    inflow_mwh.to_parquet(inflow_mwh_file)


if __name__ == "__main__":
    powerplants_get_inflow_mwh(
        inflow_m3_file=snakemake.input.inflow_m3,
        powerplants_file=snakemake.input.adjusted_powerplants,
        statistics_file=snakemake.input.statistics,
        capacity_factor_range=snakemake.params.capacity_factor_range,
        technology_mapping=snakemake.params.technology_mapping,
        inflow_mwh_file=snakemake.output.inflow_mwh,
    )
