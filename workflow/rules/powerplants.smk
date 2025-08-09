"""Rules for processing powerstations."""


rule powerplants_adjust_location:
    message:
        "Adjusting hydro powerplant location to the nearest shape and basin."
    params:
        crs=config["crs"],
        basin_adjustment=config["powerplants"]["basin_adjustment"],
    input:
        basins=ancient(
            f"resources/automatic/hydrobasin_global_{config["pfafstetter_level"]}.parquet"
        ),
        powerplants="resources/user/powerplants.parquet",
        shapes="resources/user/shapes.parquet",
    output:
        adjusted_powerplants="results/adjusted_powerplants.parquet",
        plot=report(
            "results/adjusted_powerplants.png",
            caption="../report/adjustment.rst",
            category="Hydropower module",
        ),
    log:
        "logs/powerplants_adjust_location.log",
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
        adjusted_powerplants="results/adjusted_powerplants.parquet",
        basins=ancient(
            f"resources/automatic/hydrobasin_global_{config["pfafstetter_level"]}.parquet"
        ),
        shapes="resources/user/shapes.parquet",
        cutout=ancient("resources/automatic/cutout.nc"),
    output:
        inflow="results/by_powerplant_id/inflow_m3.parquet",
    log:
        "logs/powerplants_get_inflow_m3.log",
    conda:
        "../envs/default.yaml"
    script:
        "../scripts/powerplants_get_inflow_m3.py"


rule powerplants_get_inflow_mwh:
    message:
        "Calculating powerplant generation in MWh and applying corrections using historical data."
    params:
        capacity_factor_range=internal["capacity_factor_range"],
    input:
        inflow_m3="results/by_powerplant_id/inflow_m3.parquet",
        adjusted_powerplants="results/adjusted_powerplants.parquet",
        national_generation="resources/user/national_generation.parquet",
    output:
        inflow_mwh="results/by_powerplant_id/inflow_mwh.parquet",
    log:
        "logs/powerplants_get_inflow_mwh.log",
    conda:
        "../envs/default.yaml"
    script:
        "../scripts/powerplants_get_inflow_mwh.py"


rule powerplants_get_cf_per_shape:
    message:
        "Calculating capacity factor timeseries per shape for '{wildcards.plant_type}'."
    input:
        adjusted_powerplants="results/adjusted_powerplants.parquet",
        inflow_mwh="results/by_powerplant_id/inflow_mwh.parquet",
    output:
        timeseries="results/by_shape_id/{plant_type}_cf.parquet",
        figure=report(
            "results/by_shape_id/{plant_type}_cf.png",
            caption="../report/cf_per_shape.rst",
            category="Hydropower module",
        ),
    wildcard_constraints:
        plant_type="|".join(["hydro_run_of_river", "hydro_dam"]),
    log:
        "logs/powerplants_get_cf_per_shape_{plant_type}.log",
    conda:
        "../envs/default.yaml"
    script:
        "../scripts/powerplants_get_cf_per_shape.py"
