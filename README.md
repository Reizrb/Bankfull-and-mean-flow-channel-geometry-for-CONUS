<img src="assets/banner.png" alt="Bankfull and Mean-flow Channel Geometry for CONUS" width="100%">

# Bankfull and Mean-flow Channel Geometry Estimation for CONtiguous United States (CONUS)

This GitHub repository represents the outcomes, datasets, codes, and script of "Bankfull and Mean-flow Channel Geometry Estimation Through Machine Learning  Algorithms Across the CONtiguous United States (CONUS)" research project. 

Citation to the corresponding paper: Zarrabi, R., McDermott, R., Erfani, S. M. H., & Cohen, S. (2025). Bankfull and Mean‐Flow channel geometry estimation through machine learning algorithms across the CONtiguous United States (CONUS). Water Resources Research, 61(2). https://doi.org/10.1029/2024wr037997

## Get the data

- **Full dataset (latest version):** [Zenodo](https://zenodo.org/records/19208847) (doi:10.5281/zenodo.19208847) and [HydroShare](https://www.hydroshare.org/resource/1a2e115c212f4f4a80660f94339205e6/), CC-BY-4.0
- **Just the reaches or gages you need:** use the web page and API at **https://conus-channel-geometry.onrender.com**. Select reaches or USGS gages by COMID, site number, state, HUC2, HUC8, or an area on the map, and download them as CSV, GeoJSON, or a shapefile. See the [Data API](DataAPI/) folder for details and code examples.

Quick example in Python:

```python
import io, pandas as pd, requests

r = requests.post("https://conus-channel-geometry.onrender.com/extract",
                  json={"request_type": "huc8", "huc8": "03160112", "format": "csv"})
reaches = pd.read_csv(io.StringIO(r.text), dtype={"reachcode": str, "huc2": str, "huc8": str})
```

## Repository structure

| Folder | Contents |
|--------|----------|
| [DataPreProcessing](DataPreProcessing/) | Preparing and filtering the training data |
| [ModelDevelopment](ModelDevelopment/) | MLR, RFR, and XGBR models and tuned parameters |
| [ModelIndependentEvaluation](ModelIndependentEvaluation/) | Independent evaluation of the models |
| [ModelApplication](ModelApplication/) | Applying the final models to NHDPlusV2.1 reaches |
| [DataAPI](DataAPI/) | Web page and API serving the predicted channel geometry |


![AGU2025_RZ_page-0001 (1)](https://github.com/user-attachments/assets/ac4e0f46-4a39-429e-a2c8-3e2a61426dc7)
<div align="center">
    The presented poster for the American Geophysics Union (AGU) 2025, New Orleans, LA, USA.
</div>
