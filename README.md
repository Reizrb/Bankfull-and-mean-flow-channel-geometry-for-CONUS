# Bankfull and Mean-flow Channel Geometry Estimation for CONUS

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23520140.svg)](https://doi.org/10.5281/zenodo.23520140)

This repository contains the data processing, model development, evaluation, and
application code for:

> Zarrabi, R., McDermott, R., Erfani, S. M. H., & Cohen, S. (2025). Bankfull and
> mean-flow channel geometry estimation through machine learning algorithms across
> the CONtiguous United States (CONUS). *Water Resources Research*, 61(2).
> https://doi.org/10.1029/2024WR037997

The project estimates **bankfull width, bankfull depth, mean-flow width, and
mean-flow depth** for river reaches across the conterminous United States, using
statistical and machine-learning models trained on USGS field measurements.

## Workflow

1. **Data and preprocessing** ([DataPreProcessing](DataPreProcessing/)).
   Channel and flow measurements from the USGS HYDRoSWOT dataset (more than 10,000
   stream gages) are cleaned and quality-controlled, and bankfull and mean-flow
   observations are identified.
2. **Model development** ([ModelDevelopment](ModelDevelopment/)).
   For each of the four target variables, two model types are built:
   - **Model 1** uses HYDRoSWOT-derived discharge (bankfull Q<sub>bnk</sub> or
     mean-flow Q<sub>mf</sub>).
   - **Model 2** uses NHDPlusV2.1-derived mean annual flow (Q<sub>E</sub>), so it
     can be applied to any NHDPlusV2.1 reach.

   Each is trained with three methods: Multi-Linear Regression (MLR), Random Forest
   Regression (RFR), and eXtreme Gradient Boosting Regression (XGBR). Tuned
   parameters are saved in each method's `Best_Param` folder.
3. **Independent evaluation** ([ModelIndependentEvaluation](ModelIndependentEvaluation/)).
   Mean-flow predictions are evaluated against US Army Corps of Engineers eHydro
   surveys, and bankfull predictions against regional survey data from 11
   published sources.
4. **Application** ([ModelApplication](ModelApplication/)).
   Model 2 with XGBR is applied to NHDPlusV2.1 reaches across CONUS to produce
   the final dataset.

## Repository structure

```
DataPreProcessing/            Data sources and quality-control steps
ModelDevelopment/
├── MLR/                      Multi-Linear Regression notebooks (Model 1 and 2)
├── RFR/                      Random Forest notebooks and tuned parameters
└── XGBR/                     XGBoost notebooks and tuned parameters
ModelIndependentEvaluation/   Bankfull and mean-flow evaluation notebooks
ModelApplication/             Prediction notebooks for the four variables across CONUS
```

Each folder has its own Readme with details, tables, and figures.

## Results and data

The final dataset contains predicted bankfull and mean-flow width and depth for
2,642,259 NHDPlusV2.1 reaches, available on
[Zenodo](https://doi.org/10.5281/zenodo.19208847) and
[HydroShare](https://www.hydroshare.org/resource/1a2e115c212f4f4a80660f94339205e6/)
(CC-BY-4.0).

To get the data for specific reaches or areas without downloading the full
dataset, use [HydroGeom](https://github.com/Reizrb/HydroGeom): the
[web page](https://conus-channel-geometry.onrender.com), the
[API](https://conus-channel-geometry.onrender.com/docs), or the HydroGeomKit
Python package (`pip install "git+https://github.com/Reizrb/HydroGeom"`).

## Citation

If you use this code or data, please cite the paper above and the dataset
(doi:10.5281/zenodo.19208847).

## Funding

<table><tr>
<td width="110"><img src="assets/ciroh_logo.png" alt="CIROH logo" width="100"></td>
<td>Funding for this project was provided by the National Oceanic &amp; Atmospheric Administration (NOAA), awarded to the Cooperative Institute for Research to Operations in Hydrology (CIROH) through the Cooperative Agreement with The University of Alabama (NA22NWS4320003).</td>
</tr></table>

## License

Code: [MIT](LICENSE). Data: CC-BY-4.0.

## Related repositories

| Repository | What it does |
|------------|--------------|
| [Bankfull-and-mean-flow-channel-geometry-for-CONUS](https://github.com/Reizrb/Bankfull-and-mean-flow-channel-geometry-for-CONUS) | ML models and the CONUS bankfull and mean-flow channel geometry dataset (this repository) |
| [HydroGeom](https://github.com/Reizrb/HydroGeom) | Web page, API, and Python package to get and use the channel geometry |
| [Bathymetric-Adjustment-of-Rating-Curves-and-Stage-Shift-BARC-SS](https://github.com/Reizrb/Bathymetric-Adjustment-of-Rating-Curves-and-Stage-Shift-BARC-SS) | Adds the channel geometry to OWP HAND-FIM rating curves for flood mapping (BARC, BARC-SS) |
| [TRoute-Channel-Geometry](https://github.com/Reizrb/TRoute-Channel-Geometry) | Adds the channel geometry to the NWM RouteLink file for T-Route routing |

---

![AGU2025 poster](https://github.com/user-attachments/assets/ac4e0f46-4a39-429e-a2c8-3e2a61426dc7)
<p align="center">Poster presented at AGU 2025, New Orleans, LA, USA.</p>
