"""Rules to used to download automatic resource files."""


rule download_eia:
    message:
        "Download the EIA International energy statistics in bulk."
    params:
        url=internal["resources"]["automatic"]["EIA"],
    output:
        zipfile="<resources>/automatic/eia/EIA-INTL.zip",
    log:
        "<logs>/download_eia.log",
    localrule: True
    conda:
        "../envs/shell.yaml"
    shell:
        r'curl -fsSLo {output.zipfile:q} "{params.url}"'


rule download_basin:
    message:
        "Downloading HydroBASINS file for '{wildcards.continent}'."
    params:
        url=lambda wc: internal["resources"]["automatic"]["HydroBASINS"].format(
            continent=wc.continent
        ),
    output:
        path="<resources>/automatic/hydrobasins/{continent}.zip",
    wildcard_constraints:
        continent="|".join(internal["continent_codes"]),
    conda:
        "../envs/shell.yaml"
    log:
        "<logs>/download_basin_{continent}.log",
    localrule: True
    shell:
        r'curl -fsSLo {output.path:q} "{params.url}"'


rule download_cutout:
    message:
        "Downloading runoff cutout from {params.start_year}-01-01 to {params.end_year}-12-31."
    params:
        era5_crs=internal["era5_crs"],
        start_year=config["years"]["start"],
        end_year=config["years"]["end"],
    input:
        shapes="<shapes>",
    output:
        cutout="<resources>/automatic/shapes/{shapes}/cutout.nc",
        plot=report(
            "<resources>/automatic/shapes/{shapes}/cutout.png",
            caption="../report/cutout.rst",
            category="Hydropower module",
        ),
    conda:
        "../envs/hydropower.yaml"
    log:
        "<logs>/{shapes}/download_cutout.log",
    localrule: True
    script:
        "../scripts/download_cutout.py"
