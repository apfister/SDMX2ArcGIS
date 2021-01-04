# SDMX2ArcGIS

## Objective

This project provides a [Python Toolbox](https://pro.arcgis.com/en/pro-app/latest/arcpy/geoprocessing_and_python/a-quick-tour-of-python-toolboxes.htm) that will allow someone to take the JSON response from an SDMX Query and create feature classes by joining it to a geography layer.

## Background

SDMX, which stands for [Statistical Data and Metadata eXchange](https://sdmx.org/), is an international initiative that aims at standardising and modernising (“industrialising”) the mechanisms and processes for the exchange of statistical data and metadata among international organisations and their member countries.

Serving a global user community in the Statistics Industry (and beyond), SDMX is a valuable initiative that can add tremendous value to the GIS community when brought into ArcGIS.

## Requirements

- ArcGIS Pro

## Getting Started

1. Clone/download the Python Toolbox from this repo
2. Add it to ArcGIS Pro
   - Open an ArcGIS Pro project
   - Navigate to the **Catalog** pane
   - Expand the **Toolboxes**
   - Right-click on **Add Toolbox**
   - Click on **Add Toolbox**
   - Navigate to where you downloaded this Python Toolbox and select it
3. Expand the **SDMX2ArcGIS** Toolbox where you will see a single tool titled, "SDMX API to Feature Class"
4. Double-click on that tool and it will open in the **Geoprocessing** pane

## Documentation

For details on how to run the tool, its parameters/limitations/etc., please visit the [Wiki](https://github.com/apfister/SDMX2ArcGIS/wiki/Documentation).
