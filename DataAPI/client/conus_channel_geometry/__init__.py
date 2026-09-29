"""
conus_channel_geometry
======================

Get machine-learning estimates of bankfull and mean-flow channel width and depth
for NHDPlusV2.1 reaches and USGS gages across the conterminous United States,
from the Channel Geometry API (https://conus-channel-geometry.onrender.com).

    >>> from conus_channel_geometry import get_channel_geometry
    >>> reaches = get_channel_geometry(huc8="03160112")

If you use this data, please cite:
Zarrabi, R., McDermott, R., Erfani, S. M. H., & Cohen, S. (2025). Bankfull and
mean-flow channel geometry estimation through machine learning algorithms across
the CONtiguous United States (CONUS). Water Resources Research, 61(2).
https://doi.org/10.1029/2024WR037997
"""
from .api import (
    DEFAULT_URL,
    ChannelGeometryError,
    TooManyRecords,
    get_channel_geometry,
    status,
)

__version__ = "0.1.0"
__all__ = ["get_channel_geometry", "status", "ChannelGeometryError", "TooManyRecords",
           "DEFAULT_URL", "__version__"]
