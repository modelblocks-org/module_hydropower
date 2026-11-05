"""Rules to used to download automatic resource files."""


rule download_eia:
    output:
        zipfile="<resources>/automatic/eia/EIA-INTL.zip",
    log:
        "<logs>/download_eia.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["EIA"],
    message:
        "Download the EIA International energy statistics in bulk."
    shell:
        'curl -fsSLo {output.zipfile:q} "{params.url}" 2>{log:q}'


rule download_basin:
    output:
        path="<resources>/automatic/hydrobasins/{continent}.zip",
    log:
        "<logs>/download_basin_{continent}.log",
    wildcard_constraints:
        continent="|".join(internal["continent_codes"]),
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        url=lambda wc: internal["resources"]["automatic"]["HydroBASINS"].format(
            continent=wc.continent
        ),
    message:
        "Downloading HydroBASINS file for '{wildcards.continent}'."
    shell:
        'curl -fsSLo {output.path:q} "{params.url}" 2>{log:q}'


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
        "../envs/module.yaml"
    params:
        era5_crs=internal["era5_crs"],
        start_year=config["years"]["start"],
        end_year=config["years"]["end"],
    message:
        "Downloading runoff cutout from {params.start_year}-01-01 to {params.end_year}-12-31."
    script:
        "../scripts/download_cutout.py"


rule download_glofas_uparea:
    output:
        uparea="<resources>/automatic/glofas/uparea.nc",
    log:
        "<logs>/download_glofas_uparea.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        url=internal["resources"]["automatic"]["GloFAS_uparea"],
    message:
        "Download the GloFAS upstream area map."
    shell:
        'curl -fsSLo {output.uparea:q} "{params.url}" 2>{log:q}'


rule download_glofas_discharge:
    input:
        shapes="<shapes>",
    output:
        discharge="<resources>/automatic/shapes/{shapes}/glofas_discharge.nc",
    log:
        "<logs>/{shapes}/download_glofas_discharge.log",
    localrule: True
    conda:
        "../envs/module.yaml"
    params:
        settings=internal["glofas"],
        crs=internal["era5_crs"],
        # Pad the area so that the search window of border powerplants stays inside it
        padding_deg=(config["inflow"]["glofas"]["search_window_cells"] + 1)
        * internal["glofas"]["cell_deg"],
        start_year=config["years"]["start"],
        end_year=config["years"]["end"],
    message:
        "Downloading GloFAS river discharge from {params.start_year}-01-01 to {params.end_year}-12-31."
    script:
        "../scripts/download_glofas_discharge.py"
