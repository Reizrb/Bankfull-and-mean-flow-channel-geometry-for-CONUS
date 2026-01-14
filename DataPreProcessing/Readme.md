Data Sets and Pre-Processing

This project utilizes the HYDRoSWOT data set, which provides channel and flow measurements collected at over 10,000 USGS stream gages across the United States. Initial attributes include discharge, depth, width, cross-sectional area, and velocity. The raw data contain incomplete and inconsistent values, so an extensive preprocessing workflow was applied to improve data reliability and usability for modeling.

Data cleaning and quality control steps included:

1. Removing observations with zero, null, or negative hydraulic values.
2. Filtering to retain only USGS stream gages classified as stream channels.
3. Eliminating records where mean values exceeded maximum values (e.g., mean depth > max depth).
4. Applying a discharge consistency check to remove observations with more than 5% discrepancy among measured, estimated, and velocity-derived discharge values.

After cleaning, the HYDRoSWOT data set was reduced from ~223k observations to ~38k observations from ~4,600 sites. This cleaned version is referred to as HYDRoSWOT_init.

Bankfull and mean-flow extraction:

Bankfull conditions were estimated for each site using the width-to-depth ratio response to discharge. A breakpoint in this relationship was identified via an interquartile range (IQR) method to separate within-channel and overbank observations. The selected bankfull record corresponds to the highest discharge within the within-channel domain.

Mean-flow conditions were extracted by selecting the observation closest to the NHDPlusV2.1 mean annual flow estimate for each site.

Integration with NHDPlusV2.1 and landscape attributes:

Each USGS gage site and associated hydraulic attributes were linked to reach-based properties from NHDPlusV2.1.

Additional predictive variables (e.g., population density, land cover, soil composition, vegetation indices, number of upstream dams) were incorporated from supplementary NAWQA-linked data.

Median sediment particle size (D50) and Aridity Index (AI) were added to represent geomorphic and climatic controls.

Final modeling data set:

The compiled data set consists of reach-averaged predictors and hydraulic geometry targets (bankfull and mean-flow).

The final data set includes 2,626 USGS gage sites across the continental U.S.

Data were shuffled and split into training and testing subsets using a 75/25% ratio.
