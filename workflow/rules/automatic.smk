"""Rules to used to download automatic resource files."""


rule download_eia:
    output:
        zipfile="<resources>/automatic/eia/EIA-INTL.zip",
    log:
        "<logs>/download_eia.log",
    localrule: True
    conda:
        "../envs/shell.yaml"
    params:
        url=internal["resources"]["automatic"]["EIA"],
    message:
        "Download the EIA International energy statistics in bulk."
    shell:
        r'curl -fsSLo {output.zipfile:q} "{params.url}"'


rule download_basin:
    output:
        path="<resources>/automatic/hydrobasins/{continent}.zip",
    log:
        "<logs>/download_basin_{continent}.log",
    wildcard_constraints:
        continent="|".join(internal["continent_codes"]),
    localrule: True
    conda:
        "../envs/shell.yaml"
    params:
        url=lambda wc: internal["resources"]["automatic"]["HydroBASINS"].format(
            continent=wc.continent
        ),
    message:
        "Downloading HydroBASINS file for '{wildcards.continent}'."
    shell:
        r'curl -fsSLo {output.path:q} "{params.url}"'


rule download_cutout:
    input:
        shapes="<shapes>",
    output:
        cutout="<resources>/automatic/shapes/{shapes}/cutout.nc",
        plot=report(
            "<resources>/automatic/shapes/{shapes}/cutout.png",
            caption="../report/cutout.rst",
            category="Hydropower module",
        ),
    log:
        "<logs>/{shapes}/download_cutout.log",
    localrule: True
    conda:
        "../envs/hydropower.yaml"
    params:
        era5_crs=internal["era5_crs"],
        start_year=config["years"]["start"],
        end_year=config["years"]["end"],
    message:
        "Downloading runoff cutout from {params.start_year}-01-01 to {params.end_year}-12-31."
    script:
        "../scripts/download_cutout.py"
