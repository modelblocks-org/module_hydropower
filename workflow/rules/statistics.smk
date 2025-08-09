"""Rules for collating and preparing hydropower national statistics."""


rule prepare_statistics:
    message:
        "Get EIA annual country hydropower generation statistics."
    input:
        shapes="resources/user/{shapes}/shapes.parquet",
        eia_bulk="resources/automatic/downloads/EIA-INTL.txt",
    output:
        generation="results/{shapes}/statistics/generation.parquet",
        plot="results/{shapes}/statistics/generation.pdf",
    log:
        "logs/{shapes}/prepare_statistics.log",
    conda:
        "../envs/default.yaml"
    script:
        "../scripts/prepare_statistics.py"
