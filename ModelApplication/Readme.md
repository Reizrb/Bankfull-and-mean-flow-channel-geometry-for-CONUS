# Bankfull and Mean-flow Channel Geometry Estimation for CONUS

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
dataset, use the [web page](https://conus-channel-geometry.onrender.com), the
[HydroGeomKit](https://github.com/Reizrb/HydroGeomKit) Python package, or
[HydroGeomAPI](https://github.com/Reizrb/HydroGeomAPI).

## Citation

If you use this code or data, please cite the paper above and the dataset
(doi:10.5281/zenodo.19208847).

## License

Code: [MIT](LICENSE). Data: CC-BY-4.0.

## Related repositories

| Repository | What it does |
|------------|--------------|
| [Bankfull-and-mean-flow-channel-geometry-for-CONUS](https://github.com/Reizrb/Bankfull-and-mean-flow-channel-geometry-for-CONUS) | The research: model development, evaluation, and the dataset (this repository) |
| [HydroGeomKit](https://github.com/Reizrb/HydroGeomKit) | Python package: get the data and compute channel hydraulics |
| [HydroGeomAPI](https://github.com/Reizrb/HydroGeomAPI) | The web page and API that serve the data |

---

![AGU2025 poster](https://github.com/user-attachments/assets/ac4e0f46-4a39-429e-a2c8-3e2a61426dc7)
<p align="center">Poster presented at AGU 2025, New Orleans, LA, USA.</p>
