# MEDEA-adapted Census Scraper & Visualisation Pipeline

This repository contains a Python-based pipeline to download, parse, and process Spanish 2021 Census data from the *Instituto Nacional de Estadística* (INE) at the census tract (*sección censal*) level. It calculates a **MEDEA-adapted deprivation index** (often referred to as MEDEA-like, as the full original MEDEA dataset contains certain sensitive/restricted variables that could not be accessed due to privacy constraints) using Principal Component Analysis (PCA) and produces interactive geographic maps.

## Motivation & Background

This project was born out of curiosity to inspect a deprivation map of Spain similar to the Index of Multiple Deprivation (IMD) or the Scottish Index of Multiple Deprivation (SIMD) used in Great Britain. 

However, searching for equivalent official maps in Spain yielded only an income map provided by the INE (*Atlas de Distribución de Renta de los Hogares*). Income alone does not equate to multidimensional deprivation and can be highly misleading. The search for a better alternative led to the *Atlas de la Vulnerabilidad Urbana*, but its links and resources were unfortunately broken and did not function.

Further research revealed the MEDEA deprivation index—designed for small areas in Spain, which uses variables that can be pulled directly from the public census datasets on the INE.

The resulting pipeline is fully dynamic and can be executed for any of the 52 Spanish provinces.

---

## Table of Contents
1. [Overview of the MEDEA Index](#overview-of-the-medea-index)
2. [Prerequisites & Installation](#prerequisites--installation)
3. [Pipeline Architecture & Components](#pipeline-architecture--components)
4. [Step-by-Step Execution Guide](#step-by-step-execution-guide)
5. [Project Structure](#project-structure)
6. [Design & Technical Decisions](#design--technical-decisions)

---

## Overview of the MEDEA Index

The MEDEA (Mortality in Small Areas and Socioeconomic Environment in Spain) index is a composite socioeconomic deprivation index. At the census tract level, it is calculated from three primary indicators extracted from census tables:
- **Unemployment Percentage**: Unemployed population divided by the active population.
- **Manual Workers Percentage**: Employed population working in manual occupations (e.g., machinery operators, manual labourers, agricultural workers) divided by the total employed population.
- **Low Education Percentage**: Population aged 16 and over with low educational attainment (uneducated or only primary/compulsory secondary education) divided by the total population aged 16 and over.

A Principal Component Analysis (PCA) model is trained on these three indicators to compute a single deprivation score for each census tract.

---

## Prerequisites & Installation

### 1. Requirements
- Python 3.10+ (Note: `pyproject.toml` is configured to target `>=3.14`)
- Poetry (recommended) or `pip`

### 2. Installation
Clone the repository and install the dependencies. Using Poetry:
```powershell
poetry install
```

This will automatically install required packages including `pandas`, `scikit-learn`, `geopandas`, `folium`, `mapclassify`, `matplotlib`, and `requests`.

---

## Pipeline Architecture & Components

The pipeline consists of the following modular scripts located in the `src/` directory:

1. **`build_table_registry.py`**: A one-time helper script that scans the INE JaxiT3 tables (in ranges `66600-66799`, `69100-69299`, and `69900-70199`) to identify the dynamic, non-sequential table IDs assigned to each province. It saves this mapping to `data/ine_table_registry.json`.
2. **`download_shapefiles.py`**: Downloads and extracts the official 2021 census tract cartography shapefiles from the INE server, saving them to `data/Seccionado_2021/`.
3. **`downloader.py`**: Instantiated with a 2-digit province code (e.g. `04` for Almería). It queries `data/ine_table_registry.json` to obtain the correct INE JaxiT3 table IDs for that province and downloads the CSV files.
4. **`parser.py`**: Parses the downloaded raw CSV files, handles character encoding (UTF-8-SIG), standardises headers, and extracts the raw counts for active, unemployed, employed, manual workers, and low-education populations.
5. **`medea.py`**: Implements the mathematical formula to compute percentages for each indicator and fits a Scikit-Learn PCA model to compute the final MEDEA score.
6. **`db.py`**: A SQLite database manager (`DatabaseManager`) that stores raw counts, intermediate percentages, and final MEDEA scores in `data/medea_census_<province_code>.db`.
7. **`main.py`**: The main orchestrator that downloads, parses, processes, and saves the data for a specified province code.
8. **`visualize.py`**: Visualises the computed MEDEA scores on an interactive choropleth map. It filters the national shapefile for the target province, merges it with the SQLite results, and saves a Folium-based HTML map.

---

## Step-by-Step Execution Guide

To run the pipeline and generate an interactive map for a province (e.g., Almería, code `04`):

### Step 1: Initialise the Table Registry
*(Note: A pre-built registry is already included in `data/ine_table_registry.json`. You only need to run this if the registry is missing or if the INE table IDs change.)*
```powershell
python src/build_table_registry.py
```

### Step 2: Download Census Tract Shapefiles
Download the official 2021 boundary shapefiles:
```powershell
python src/download_shapefiles.py 2021
```
This extracts the cartography files into `data/Seccionado_2021/`.

### Step 3: Run the Processing Pipeline
Run the main pipeline for Almería (code `04`):
```powershell
python src/main.py 04
```
This script will:
1. Lookup the JaxiT3 table IDs for Almería in the registry.
2. Download the census CSV files (`activity_04.csv`, `occupation_04.csv`, `situation_04.csv`, `studies_04.csv`) to `data/`.
3. Parse the data and calculate the indicators.
4. Run the PCA model.
5. Save the output database to `data/medea_census_04.db`.

### Step 4: Generate the Interactive Map
Produce an interactive HTML map showing census tracts shaded by their relative deprivation score (quantiles):
```powershell
python src/visualize.py 04
```
This creates **`data/medea_map_04.html`**. Open this file in any web browser to view the interactive map, hover over tracts to inspect details, and pan/zoom.

---

## Project Structure

```text
MEDEA/
├── data/
│   ├── Seccionado_2021/            # Extracted shapefiles (from download_shapefiles.py)
│   ├── ine_table_registry.json     # Map of province codes to JaxiT3 CSV table IDs
│   ├── *_04.csv                    # Downloader outputs (example for Almería)
│   ├── medea_census_04.db          # Intermediate database (example for Almería)
│   └── medea_map_04.html           # Interactive HTML map (example for Almería)
├── src/
│   ├── __init__.py
│   ├── api.py                      # (Legacy) Early INE API explorer
│   ├── build_table_registry.py     # Registry scraper
│   ├── db.py                       # SQLite database manager
│   ├── download_shapefiles.py      # Cartography downloader
│   ├── downloader.py               # INE CSV downloader
│   ├── main.py                     # Pipeline orchestrator
│   ├── medea.py                    # PCA calculator
│   ├── parser.py                   # CSV data parser
│   ├── scraper.py                  # Web scraper utilities
│   └── visualize.py                # Folium/GeoPandas visualisation tool
├── pyproject.toml                  # Poetry configuration and project dependencies
└── README.md                       # This documentation file
```

---

## Design & Technical Decisions

- **JaxiT3 vs. Broken INE API**: The primary INE JSON API (`Censo2021/api`) frequently returns HTTP 404/500 errors for detailed census queries. The pipeline instead uses the reliable bulk `jaxiT3` CSV export service.
- **Dynamic Table Mapping**: JaxiT3 table IDs are not contiguous or mathematically predictable because they are grouped by Spanish Autonomous Communities. `build_table_registry.py` solves this by programmatically probing and mapping IDs to provinces.
- **Character Encoding**: Census CSVs are encoded in `UTF-8-SIG` (UTF-8 with a byte order mark), which is handled explicitly in the parser to avoid character corruption.
- **SQLite Database**: Storing census tract counts in SQLite ensures that researchers can query intermediate variables or extend the pipeline with new indicators in the future.
