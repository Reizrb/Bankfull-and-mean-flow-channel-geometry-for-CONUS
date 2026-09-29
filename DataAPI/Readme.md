<img src="../assets/banner.png" alt="Bankfull and Mean-flow Channel Geometry for CONUS" width="100%">

# Data API

**Live at: https://conus-channel-geometry.onrender.com**

A web page and API for downloading machine-learning estimates of bankfull and
mean-flow channel width and depth for **2,691,339 NHDPlusV2.1 reaches** and
**28,164 USGS gages** across the conterminous United States.

Instead of downloading the full 2.5 GB release, you can get just the reaches or
gages you need, selected by ID, state, HUC2, HUC8, or an area on a map, as CSV,
GeoJSON, or a zipped shapefile.

This folder is part of the [Bankfull and Mean-flow Channel Geometry for CONUS](../)
repository. The code that produced the dataset is in the other folders.

## Using the web page

Open https://conus-channel-geometry.onrender.com and:

1. Choose **River reaches** or **USGS gages**.
2. Choose where: a HUC8 watershed, a state, a HUC2 region, a list of IDs, an area
   you draw on the map, a shapefile you upload, or all of CONUS (gages only).
3. Choose a format and click **Download data**.
4. Click **Show these on the map** to see the results. Click a reach or gage for
   its width and depth.

The map offers USGS shaded relief with the NHD river network, OpenTopoMap, and
satellite imagery, and the page has light and dark themes.

## What you get

| Column      | Description        | Units |
|-------------|--------------------|-------|
| `bnk_width` | Bankfull width     | m     |
| `bnk_depth` | Bankfull depth     | m     |
| `mf_width`  | Mean-flow width    | m     |
| `mf_depth`  | Mean-flow depth    | m     |

**Reaches** also include `comid`, `reachcode`, `state`, `huc2`, `huc8`,
`stream_order`, and `tot_da_sqkm` (total drainage area, km²).
**Gages** also include `site_no`, `station_nm`, `comid` (the reach the gage is on),
`reachcode`, `state`, `huc2`, `huc8`, `da_sqkm` (drainage area, km²), `lat`, and `lon`.

### Formats and limits

| Format    | Contents                                  | Records per download |
|-----------|-------------------------------------------|----------------------|
| CSV       | Values only, no line shapes               | up to 500,000        |
| GeoJSON   | Values plus reach lines or gage points    | up to 50,000         |
| Shapefile | Values plus reach lines or gage points (zipped) | up to 50,000   |

A CSV covers any single state or HUC2 region. For all of CONUS, download the full
dataset from Zenodo (links below).

### Good to know

- **Missing predictions:** reaches and gages without a prediction are still
  returned, with empty width and depth values, so every ID you ask for comes back.
- **Leading zeros:** HUC codes, reach codes, and USGS site numbers keep their
  leading zeros (for example `03160112`). Excel drops them when it opens a CSV, so
  import those columns as text, or read the file with Python or R.
- **Coordinate system:** geometries are in NAD83 (EPSG:4269), the NHDPlusV2.1
  system. Drawn polygons and uploaded shapefiles in any coordinate system are
  converted automatically.
- **Shapefile column names** are limited to 10 characters, so `stream_order`
  becomes `stream_ord` and `tot_da_sqkm` becomes `tot_da_sqk`. CSV and GeoJSON
  keep the full names.
- **Speed:** the service currently runs on a small free server. Most requests take
  a few seconds, and a whole state or HUC2 region can take a minute or more.

## Using the API from code

Send a `POST` request to `/extract` with a JSON body:

| Field          | Values                                                  |
|----------------|---------------------------------------------------------|
| `dataset`      | `reach` (default) or `gage`                             |
| `request_type` | `ids`, `state`, `huc2`, `huc8`, `polygon`, or `conus`   |
| `format`       | `csv` (default), `geojson`, or `shapefile`              |

Add the value for your request type: `ids` (a list of COMIDs for reaches, or USGS
site numbers for gages, written as text so leading zeros are kept, such as `"02465000"`), `state` (such as `"AL"`), `huc2` (such as `"03"`), `huc8`
(such as `"03160112"`), or `polygon` (a GeoJSON geometry in longitude/latitude).

### Python

```python
import io
import pandas as pd
import requests

API = "https://conus-channel-geometry.onrender.com/extract"

# All reaches in one HUC8, as a table
r = requests.post(API, json={"request_type": "huc8", "huc8": "03160112", "format": "csv"})
r.raise_for_status()
reaches = pd.read_csv(io.StringIO(r.text), dtype={"reachcode": str, "huc2": str, "huc8": str})

# Specific reaches by COMID
r = requests.post(API, json={"request_type": "ids", "ids": [18223451, 721640]})
by_comid = pd.read_csv(io.StringIO(r.text))

# USGS gages in a state, with their points, as GeoJSON
import geopandas as gpd
r = requests.post(API, json={"dataset": "gage", "request_type": "state",
                             "state": "AL", "format": "geojson"})
gages = gpd.read_file(io.BytesIO(r.content))
```

### R

```r
library(httr2)
library(readr)

api <- "https://conus-channel-geometry.onrender.com/extract"

resp <- request(api) |>
  req_body_json(list(request_type = "huc8", huc8 = "03160112", format = "csv")) |>
  req_perform()

reaches <- read_csv(resp_body_string(resp),
                    col_types = cols(reachcode = "c", huc2 = "c", huc8 = "c"))
```

### Command line

```bash
curl -X POST https://conus-channel-geometry.onrender.com/extract \
  -H "Content-Type: application/json" \
  -d '{"request_type": "huc8", "huc8": "03160112", "format": "shapefile"}' \
  -o reaches.zip
```

### Uploading a polygon shapefile

Send a zipped shapefile (with its `.prj` file) to `POST /extract/shapefile` as a
form upload, with `format` and `dataset` as form fields:

```bash
curl -X POST https://conus-channel-geometry.onrender.com/extract/shapefile \
  -F "file=@my_area.zip" -F "format=csv" -F "dataset=reach" -o reaches.csv
```

### Other endpoints

| Endpoint  | What it returns                                            |
|-----------|------------------------------------------------------------|
| `/docs`   | Interactive API documentation, where you can try requests  |
| `/status` | Number of reaches and gages available, and the data source |
| `/health` | A quick check that the service is running                  |

### Errors

| Code | Meaning |
|------|---------|
| 400  | Something is missing or not valid, such as a HUC8 that isn't 8 digits |
| 404  | Nothing matched the request |
| 413  | Too many records for the chosen format. The message suggests CSV or a smaller area |

## How to cite

If you use this data, please cite the paper and the dataset:

- Zarrabi, R., McDermott, R., Erfani, S. M. H., & Cohen, S. (2025). Bankfull and
  mean-flow channel geometry estimation through machine learning algorithms across
  the CONtiguous United States (CONUS). *Water Resources Research*, 61(2).
  https://doi.org/10.1029/2024WR037997
- Dataset (latest version): [Zenodo](https://zenodo.org/records/19208847)
  (doi:10.5281/zenodo.19208847) and
  [HydroShare](https://www.hydroshare.org/resource/1a2e115c212f4f4a80660f94339205e6/),
  CC-BY-4.0

## How it works

The API is a Python [FastAPI](https://fastapi.tiangolo.com/) application. The data
is stored as two GeoParquet files (`reaches.parquet` and `gages.parquet`) in a
[Hugging Face dataset](https://huggingface.co/datasets/Reizrb/bankfull-meanflow-conus).
[DuckDB](https://duckdb.org/) reads only the parts of those files that a request
needs, and writes the CSV, GeoJSON, or shapefile directly, so large downloads use
little memory. The files are sorted by HUC8, which keeps regional requests fast.
The web page uses [Leaflet](https://leafletjs.com/) with basemaps from USGS The
National Map, OpenTopoMap, and Esri.

The service is packaged as a Docker container and currently runs on
[Render](https://render.com/). To point it at another storage location (such as
an S3 bucket), set the `CG_DATA_URL` environment variable to the folder that holds
the two Parquet files.

## Running it on your own computer

```bash
cd DataAPI
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Then open http://127.0.0.1:8000. Without local data files, the API reads the data
from Hugging Face automatically.

To build the data files yourself, download the reach shapefile and gage CSV from
the latest Zenodo record, plus the
[Census state boundaries](https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_500k.zip),
into this folder, then run (the reach build takes 10–30 minutes):

```bash
python prepare_data.py gage
python prepare_data.py reach
```

To check that everything works:

```bash
python test_api.py
```

To try the API without the real data, `python make_sample_data.py` builds a small
fake reach file.

## Files

| File                  | Purpose                                                        |
|-----------------------|----------------------------------------------------------------|
| `app.py`              | The API                                                        |
| `static/`             | The web page (`index.html`) and logo                           |
| `prepare_data.py`     | Builds `reaches.parquet` and `gages.parquet`, sorted by HUC8   |
| `make_sample_data.py` | Builds a small fake reach file for testing                     |
| `test_api.py`         | Checks every request type                                      |
| `requirements.txt`    | Python packages the API needs                                  |
| `Dockerfile`          | Builds the container used for hosting                          |

## License

Code: MIT (see the repository [LICENSE](../LICENSE)). Data: CC-BY-4.0 (see the
Zenodo record).
