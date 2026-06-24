"""Rules for collating and preparing hydropower national statistics."""


rule prepare_statistics:
    input:
        shapes="<shapes>",
        eia_bulk=rules.download_eia.output.zipfile,
    output:
        generation="<statistics>",
        plot="<results>/{shapes}/statistics/generation.pdf",
    log:
        "<logs>/{shapes}/prepare_statistics.log",
    conda:
        "../envs/module.yaml"
    params:
        years=config["years"],
    message:
        "Get EIA annual country hydropower generation statistics."
    script:
        "../scripts/prepare_statistics.py"
