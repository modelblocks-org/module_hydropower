"""Rules for processing powerstations."""


rule powerplants_adjust_location:
    message:
        "Adjusting hydro powerplant location to the nearest shape and basin."
    params:
        crs=config["crs"],
        basin_adjustment=config["powerplants"]["basin_adjustment"],
    input:
        basins=f"resources/automatic/hydrobasin_global_{config["pfafstetter_level"]}.parquet",
        powerplants="resources/user/{shapes}/powerplants.parquet",
        shapes="resources/user/{shapes}/shapes.parquet",
    output:
        adjusted_powerplants="resources/automatic/{shapes}/adjusted_powerplants.parquet",
        plot=report(
            "resources/automatic/{shapes}/adjusted_powerplants.png",
            caption="../report/adjustment.rst",
            category="Hydropower module",
        ),
    log:
        "logs/{shapes}/powerplants_adjust_location.log",
    conda:
        "../envs/default.yaml"
    script:
        "../scripts/powerplants_adjust_location.py"


rule powerplants_get_inflow_m3:
    message:
        "Calculating hydro powerplant inflow in m3."
    params:
        smoothing_hours=config["smoothing_hours"],
    input:
        adjusted_powerplants="resources/automatic/{shapes}/adjusted_powerplants.parquet",
        basins=f"resources/automatic/hydrobasin_global_{config["pfafstetter_level"]}.parquet",
        shapes="resources/user/{shapes}/shapes.parquet",
        cutout="resources/automatic/{shapes}/cutout.nc",
    output:
        inflow="resources/automatic/{shapes}/disaggregated/inflow_m3.parquet",
    log:
        "logs/{shapes}/powerplants_get_inflow_m3.log",
    conda:
        "../envs/default.yaml"
    script:
        "../scripts/powerplants_get_inflow_m3.py"


rule powerplants_get_inflow_mwh:
    message:
        "Calculating powerplant generation in MWh and applying corrections using historical data."
    params:
        capacity_factor_range=internal["capacity_factor_range"],
        technology_mapping=config["powerplants"]["technology_mapping"],
    input:
        inflow_m3="resources/automatic/{shapes}/disaggregated/inflow_m3.parquet",
        adjusted_powerplants="resources/automatic/{shapes}/adjusted_powerplants.parquet",
        statistics="results/{shapes}/statistics/generation.parquet",
    output:
        inflow_mwh="results/{shapes}/disaggregated/inflow_mwh.parquet",
    log:
        "logs/{shapes}/powerplants_get_inflow_mwh.log",
    conda:
        "../envs/default.yaml"
    script:
        "../scripts/powerplants_get_inflow_mwh.py"


rule powerplants_get_cf_per_shape:
    message:
        "Calculating capacity factor timeseries per shape for '{wildcards.plant_type}'."
    params:
        technology_mapping=config["powerplants"]["technology_mapping"],
    input:
        adjusted_powerplants="resources/automatic/{shapes}/adjusted_powerplants.parquet",
        inflow_mwh="results/{shapes}/disaggregated/inflow_mwh.parquet",
    output:
        timeseries="results/{shapes}/aggregated/{plant_type}_cf.parquet",
        figure=report(
            "results/{shapes}/aggregated/{plant_type}_cf.pdf",
            caption="../report/cf_per_shape.rst",
            category="Hydropower module",
        ),
    wildcard_constraints:
        plant_type="|".join(["run_of_river", "reservoir"]),
    log:
        "logs/{shapes}/powerplants_get_cf_per_shape_{plant_type}.log",
    conda:
        "../envs/default.yaml"
    script:
        "../scripts/powerplants_get_cf_per_shape.py"
