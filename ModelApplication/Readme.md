# Final Model for Application
Although the first tier of models exhibits better accuracy, their applicability is restricted to USGS gage sites due to the requirement for Q<sub>bnk</sub>  and Q<sub>mf</sub> , which is only available for some streams in the CONUS. Consequently, the second tier of models, developed using Q<sub>E</sub>  derived from NHDPlusV2.1 and through XGBR, are chosen as the final model to predict bankfull width, bankfull depth, mean-flow width, and mean-flow depth (Figure 1 to 4).

![Bankfull_Width 2_page-0001](https://github.com/Reizrb/Bankfull-and-mean-flow-channel-geometry-for-CONUS/assets/133435701/13839000-b894-433c-baa6-ad0b6b040b29)

__Figure 1.__ _Map of predicted values of bankfull width in meter over CONtiguous United States (CONUS) for reaches/streams in the National Hydrography Dataset Plus Version 2.1 (NHDplusv2.1) with drainage area greater than 100 km<sup>2</sup>.

![Bankfull_Depth 2_page-0001](https://github.com/Reizrb/Bankfull-and-mean-flow-channel-geometry-for-CONUS/assets/133435701/322531d5-6f72-4471-a26f-9b85061cbcce)

__Figure 2.__ _Map of predicted values of bankfull depth in meter over CONtiguous United States (CONUS) for reaches/streams in the National Hydrography Dataset Plus Version 2.1 (NHDplusv2.1) with drainage area greater than 100 km<sup>2</sup>.

![Mean_Flow_Width 3](https://github.com/Reizrb/Bankfull-and-mean-flow-channel-geometry-for-CONUS/assets/133435701/c80afc7f-c849-4830-907c-5d5721741e3b)

__Figure 3.__ _Map of predicted values of mean-flow width in meter over CONtiguous United States (CONUS) for reaches/streams in the National Hydrography Dataset Plus Version 2.1 (NHDplusv2.1) with drainage area greater than 100 km<sup>2</sup>.

![Mean_Flow_Depth 3](https://github.com/Reizrb/Bankfull-and-mean-flow-channel-geometry-for-CONUS/assets/133435701/7958fb5e-b6d0-4b18-9d6d-febf06a456a0)

__Figure 4.__ _Map of predicted values of mean-flow depth in meter over CONtiguous United States (CONUS) for reaches/streams in the National Hydrography Dataset Plus Version 2.1 (NHDplusv2.1) with drainage area greater than 100 km<sup>2</sup>.

# Download Dataset
The final predicted dataset resulting from this research encompasses values of predicted width and depth under both mean-flow and bankfull conditions for 2,642,259 reaches in NHDPlusV2.1. This dataset, namely _Bankfull_Meanflow_CONUS_ is publicly available at [Zenodo](https://zenodo.org/records/13883263) and [HydroShare](https://www.hydroshare.org/resource/63ae139ccd2445959470d0e5a2ebf6a5).
