"""Rules for collating and preparing hydropower national statistics."""


rule harmonise_statistics:
    input:
        eia_bulk=rules.download_eia.output.zipfile,
    output:
        generation="<resources>/automatic/statistics/baseline.parquet",
    log:
        "<logs>/harmonise_statistics.log",
    conda:
        "../envs/module.yaml"
    message:
        "Harmonise EIA annual hydropower generation for all countries and years."
    script:
        "../scripts/harmonise_statistics.py"


rule prepare_statistics:
    input:
        shapes="<shapes>",
        statistics=rules.harmonise_statistics.output.generation,
    output:
        generation="<statistics_eia>",
        plot="<results>/{shapes}/statistics/generation.pdf",
    log:
        "<logs>/{shapes}/prepare_statistics.log",
    conda:
        "../envs/module.yaml"
    message:
        "Get EIA annual country hydropower generation statistics."
    script:
        "../scripts/prepare_statistics.py"
