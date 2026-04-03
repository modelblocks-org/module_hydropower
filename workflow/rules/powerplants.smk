"""Rules for processing powerstations."""


rule powerplants_adjust_location:
    message:
        "Adjusting hydro powerplant location to the nearest shape and basin."
    params:
        crs=config["crs"],
        basin_adjustment=config["powerplants"]["basin_adjustment"],
    input:
        basins=f"<resources>/automatic/hydrobasins/global_{config["pfafstetter_level"]}.parquet",
        powerplants="<powerplants>",
        shapes="<shapes>",
    output:
        adjusted_powerplants="<resources>/automatic/shapes/{shapes}/adjusted_powerplants.parquet",
        plot=report(
            "<resources>/automatic/shapes/{shapes}/adjusted_powerplants.png",
            caption="../report/adjustment.rst",
            category="Hydropower module",
        ),
    log:
        "<logs>/{shapes}/powerplants_adjust_location.log",
    conda:
        "../envs/hydropower.yaml"
    script:
        "../scripts/powerplants_adjust_location.py"


rule powerplants_get_inflow_m3:
    message:
        "Calculating hydro powerplant inflow in m3."
    params:
        smoothing_hours=config["smoothing_hours"],
    input:
        adjusted_powerplants=rules.powerplants_adjust_location.output.adjusted_powerplants,
        basins=f"<resources>/automatic/hydrobasins/global_{config["pfafstetter_level"]}.parquet",
        shapes="<shapes>",
        cutout=rules.download_cutout.output.cutout,
    output:
        inflow="<resources>/automatic/shapes/{shapes}/disaggregated/inflow_m3.parquet",
    log:
        "<logs>/{shapes}/powerplants_get_inflow_m3.log",
    conda:
        "../envs/hydropower.yaml"
    script:
        "../scripts/powerplants_get_inflow_m3.py"


rule powerplants_get_inflow_mwh:
    message:
        "Calculating powerplant generation in MWh and applying corrections using historical data."
    params:
        capacity_factor_range=internal["capacity_factor_range"],
        technology_mapping=config["powerplants"]["technology_mapping"],
    input:
        inflow_m3=rules.powerplants_get_inflow_m3.output.inflow,
        adjusted_powerplants=rules.powerplants_adjust_location.output.adjusted_powerplants,
        statistics="<statistics>",
    output:
        inflow_mwh="<disaggregated_inflow>",
    log:
        "<logs>/{shapes}/powerplants_get_inflow_mwh.log",
    conda:
        "../envs/hydropower.yaml"
    script:
        "../scripts/powerplants_get_inflow_mwh.py"


rule powerplants_get_cf_per_shape:
    message:
        "Calculating capacity factor timeseries per shape for '{wildcards.plant_type}'."
    params:
        technology_mapping=config["powerplants"]["technology_mapping"],
    input:
        adjusted_powerplants=rules.powerplants_adjust_location.output.adjusted_powerplants,
        inflow_mwh="<disaggregated_inflow>",
    output:
        timeseries="<aggregated_cf_timeseries>",
        figure=report(
            "<results>/{shapes}/aggregated/{plant_type}_cf.pdf",
            caption="../report/cf_per_shape.rst",
            category="Hydropower module",
        ),
    wildcard_constraints:
        plant_type="|".join(["run_of_river", "reservoir"]),
    log:
        "<logs>/{shapes}/powerplants_get_cf_per_shape_{plant_type}.log",
    conda:
        "../envs/hydropower.yaml"
    script:
        "../scripts/powerplants_get_cf_per_shape.py"
