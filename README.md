<img src="assets/banner.png" alt="Bankfull and Mean-flow Channel Geometry for CONUS" width="100%">

# Bankfull and Mean-flow Channel Geometry for CONUS

Machine-learning estimates of **bankfull and mean-flow channel width and depth** for
about 2.7 million NHDPlusV2.1 river reaches and 28,000 USGS gages across the
conterminous United States.

This repository has everything from the research to the data service: the code
used to build and evaluate the models, and the tools to access the results.

## Get the data

| Option | Best for |
|--------|----------|
| [**Web page**](https://conus-channel-geometry.onrender.com) | Picking an area on a map and downloading it as CSV, GeoJSON, or shapefile |
| [**Python package: HydroGeomKit**](DataAPI/client/) | Getting data straight into pandas or GeoPandas |
| [**API**](DataAPI/) | Scripts in any language (Python, R, command line) |
| [**Full dataset**](https://doi.org/10.5281/zenodo.19208847) | All reaches at once (Zenodo and [HydroShare](https://www.hydroshare.org/resource/1a2e115c212f4f4a80660f94339205e6/)) |

```python
# pip install "git+https://github.com/Reizrb/Bankfull-and-mean-flow-channel-geometry-for-CONUS#subdirectory=DataAPI/client"
from hydrogeomkit import get_channel_geometry

reaches = get_channel_geometry(huc8="03160112")
```

## What's in this repository

| Folder | Contents |
|--------|----------|
| **Model development** | |
| [DataPreProcessing](DataPreProcessing/) | Preparing and filtering the training data |
| [ModelDevelopment](ModelDevelopment/) | MLR, RFR, and XGBR models and tuned parameters |
| [ModelIndependentEvaluation](ModelIndependentEvaluation/) | Independent evaluation of the models |
| [ModelApplication](ModelApplication/) | Applying the final models to NHDPlusV2.1 reaches |
| **Data access** | |
| [DataAPI](DataAPI/) | Web page and API serving the results |
| [DataAPI/client](DataAPI/client/) | HydroGeomKit, the Python package (`hydrogeomkit`) |

## Citation

If you use this data or code, please cite:

Zarrabi, R., McDermott, R., Erfani, S. M. H., & Cohen, S. (2025). Bankfull and
mean-flow channel geometry estimation through machine learning algorithms across the
CONtiguous United States (CONUS). *Water Resources Research*, 61(2).
https://doi.org/10.1029/2024WR037997

Dataset: https://doi.org/10.5281/zenodo.19208847 (CC-BY-4.0)

## License

Code: [MIT](LICENSE). Data: CC-BY-4.0.

---

![AGU2025 poster](https://github.com/user-attachments/assets/ac4e0f46-4a39-429e-a2c8-3e2a61426dc7)
<p align="center">Poster presented at AGU 2025, New Orleans, LA, USA.</p>
