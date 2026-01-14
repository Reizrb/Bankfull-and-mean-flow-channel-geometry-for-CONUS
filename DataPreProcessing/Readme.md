# Datasets and Pre-Processing

This project utilizes the HYDRoSWOT data set, which provides channel and flow measurements collected at over 10,000 USGS stream gages across the United States. Initial attributes include discharge, depth, width, cross-sectional area, and velocity. The raw data contain incomplete and inconsistent values, so an extensive preprocessing workflow was applied to improve data reliability and usability for modeling.

Data cleaning and quality control steps included:
1. Removing observations with zero, null, or negative hydraulic values.
2. Filtering to retain only USGS stream gages classified as stream channels.
3. Eliminating records where mean values exceeded maximum values (e.g., mean depth > max depth).
4. Applying a discharge consistency check to remove observations with more than 5% discrepancy among measured, estimated, and velocity-derived discharge values.
5. Identifying Bankfull and mean-flow observations
