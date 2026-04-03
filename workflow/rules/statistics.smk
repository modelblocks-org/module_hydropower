"""Rules for collating and preparing hydropower national statistics."""


rule prepare_statistics:
    message:
        "Get EIA annual country hydropower generation statistics."
    params:
        years=config["years"],
    input:
        shapes="<shapes>",
        eia_bulk="<resources>/automatic/downloads/EIA-INTL.txt",
    output:
        generation="<statistics>",
        plot="<results>/{shapes}/statistics/generation.pdf",
    log:
        "<logs>/{shapes}/prepare_statistics.log",
    conda:
        "../envs/hydropower.yaml"
    script:
        "../scripts/prepare_statistics.py"
