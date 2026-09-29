# HydroGeomKit

**HydroGeomKit** (`hydrogeomkit`) is a small Python package to get machine-learning estimates of **bankfull and
mean-flow channel width and depth** for NHDPlusV2.1 reaches and USGS gages across
the conterminous United States, straight into pandas or GeoPandas.

It uses the [Channel Geometry API](https://conus-channel-geometry.onrender.com),
so there's nothing to download or unzip first.

## Install

```bash
pip install "git+https://github.com/Reizrb/Bankfull-and-mean-flow-channel-geometry-for-CONUS#subdirectory=DataAPI/client"
```

To get reach lines and gage points as a GeoDataFrame, also install GeoPandas:

```bash
pip install geopandas
```

## Use

```python
from hydrogeomkit import get_channel_geometry

# All reaches in a HUC8 watershed, as a pandas table
reaches = get_channel_geometry(huc8="03160112")

# Specific reaches by COMID
reaches = get_channel_geometry(comids=[18223451, 721640])

# A whole state or HUC2 region (values only, up to 500,000 reaches)
alabama = get_channel_geometry(state="AL")

# USGS gages, by site number (as text, to keep leading zeros)
gages = get_channel_geometry(site_nos=["02465000", "01206900"])

# Gages in a state, with their points, as a GeoDataFrame
gages = get_channel_geometry(dataset="gage", state="AL", geometry=True)

# Reaches inside your own study area (a shapely geometry, or a GeoDataFrame in any CRS)
import geopandas as gpd
basin = gpd.read_file("my_basin.shp")
reaches = get_channel_geometry(polygon=basin, geometry=True)
```

Choose **one** way to select the area: `comids`, `site_nos`, `state`, `huc2`,
`huc8`, `polygon`, or `conus=True` (gages only).

## What you get

| Column      | Description     | Units |
|-------------|-----------------|-------|
| `bnk_width` | Bankfull width  | m     |
| `bnk_depth` | Bankfull depth  | m     |
| `mf_width`  | Mean-flow width | m     |
| `mf_depth`  | Mean-flow depth | m     |

Reaches also have `comid`, `reachcode`, `state`, `huc2`, `huc8`, `stream_order`,
and `tot_da_sqkm` (total drainage area, km²). Gages also have `site_no`,
`station_nm`, `comid`, `reachcode`, `state`, `huc2`, `huc8`, `da_sqkm`, `lat`, and
`lon`. Codes (HUCs, reach codes, site numbers) are kept as text, so leading zeros
are preserved. Records without a prediction have empty (NaN) width and depth.

| `geometry=`     | Returns                              | Records per call |
|-----------------|--------------------------------------|------------------|
| `False` (default) | pandas DataFrame, values only      | up to 500,000    |
| `True`          | GeoDataFrame with lines or points (EPSG:4269) | up to 50,000 |

For all 2.7 million reaches, download the full dataset from
[Zenodo](https://doi.org/10.5281/zenodo.19208847).

## Errors

- `TooManyRecords`: the area is too big for one call. It has `.records` and
  `.limit`. Use `geometry=False`, or a smaller area.
- `ChannelGeometryError`: anything else, with the reason from the API.

The package waits and retries automatically if the server is starting up, and
waits up to 10 minutes for large areas (set `timeout=` to change this).

## Other options

- `status()` shows how many reaches and gages are available.
- `base_url=` (or the `HYDROGEOMKIT_URL` environment variable) points
  the package at another copy of the API.

## Cite

If you use this data, please cite:

Zarrabi, R., McDermott, R., Erfani, S. M. H., & Cohen, S. (2025). Bankfull and
mean-flow channel geometry estimation through machine learning algorithms across
the CONtiguous United States (CONUS). *Water Resources Research*, 61(2).
https://doi.org/10.1029/2024WR037997

Dataset: https://doi.org/10.5281/zenodo.19208847 (CC-BY-4.0)

## License

MIT
