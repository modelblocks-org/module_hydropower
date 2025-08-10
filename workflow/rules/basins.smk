"""Rules for processing the HydroBASINS dataset."""


rule basins_extract_pfafstetter_level:
    message:
        "Unzipping HydroBASINS file for '{wildcards.continent}' at Pfafstetter level '{params.level}'."
    params:
        level=lambda wc: wc.level,
        continent=lambda wc: wc.continent,
    input:
        zip_file="resources/automatic/hydrobasin_{continent}.zip",
    output:
        parquet_file=temp("resources/automatic/hydrobasin_{continent}_{level}.parquet"),
    wildcard_constraints:
        continent="|".join(internal["continent_codes"]),
        level="|".join(internal["pfafstetter_level_codes"]),
    conda:
        "../envs/default.yaml"
    log:
        "logs/basins_extract_pfafstetter_level_{continent}_{level}.log",
    script:
        "../scripts/basins_extract_pfafstetter_level.py"


rule basins_combine_continents:
    message:
        "Combine all HydroBASINS into a single dataset for Pfafstetter level '{wildcards.level}'."
    input:
        continent_files=expand(
            "resources/automatic/hydrobasin_{continent}_{{level}}.parquet",
            continent=internal["continent_codes"],
        ),
    output:
        global_file="resources/automatic/hydrobasin_global_{level}.parquet",
        plot=report(
            "resources/automatic/hydrobasin_global_{level}.png",
            caption="../report/basins.rst",
            category="Hydropower module",
        ),
    conda:
        "../envs/default.yaml"
    log:
        "logs/basins_combine_continents_{level}.log",
    script:
        "../scripts/basins_combine_continents.py"
