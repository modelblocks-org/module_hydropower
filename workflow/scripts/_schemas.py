"""Schemas for key files."""

from pandera.pandas import DataFrameModel, Field, check
from pandera.typing.geopandas import GeoSeries
from pandera.typing.pandas import Index, Series


class ShapeSchema(DataFrameModel):
    class Config:
        coerce = True
        strict = "filter"

    shape_id: Series[str] = Field(unique=True)
    "Unique ID for this shape."
    country_id: Series[str]
    "ISO alpha-3 code."
    shape_class: Series[str] = Field(isin=["land", "maritime"])
    "Shape classifier"
    geometry: GeoSeries
    "Shape polygon."

    index: Index[int] = Field(unique=True)

    @check("geometry", element_wise=True)
    def geom_not_empty(cls, geom):
        return (geom is not None) and (not geom.is_empty) and geom.is_valid


class EIAGenerationSchema(DataFrameModel):
    class Config:
        coerce = True
        strict = True

    country_id: Series[str]
    "Country ISO-3 code"
    year: Series[int]
    "Sample year"
    category: Series[str] = Field(isin=["hydropower"])
    generation_mwh: Series[float] = Field(ge=0)
    "Hydropower generation for the given year"

    index: Index[int] = Field(unique=True)


class PowerplantSchema(DataFrameModel):
    class Config:
        coerce = True
        strict = "filter"

    index: Index[int] = Field(unique=True)

    powerplant_id: Series[str] = Field(unique=True)
    "Unique ID for the powerplant."
    output_capacity_mw: Series[float] = Field(ge=0)
    "Powerplant output capacity in Megawatts."
    technology: Series[str]
    "Powerplant technology (e.g., run of river, basin)."
    # Temporal aspects
    start_year: Series[float] = Field(ge=0)
    "Installation year."
    end_year: Series[float] = Field(ge=0)
    "Expected decommissioning year."
    # Location
    geometry: GeoSeries
    "Powerplant point data."
