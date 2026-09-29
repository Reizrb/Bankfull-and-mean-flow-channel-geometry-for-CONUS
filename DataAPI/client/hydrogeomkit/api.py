"""Client for the Channel Geometry API."""
from __future__ import annotations

import io
import json
import os
import time
from typing import Iterable, Optional, Union

import pandas as pd
import requests

DEFAULT_URL = os.environ.get("HYDROGEOMKIT_URL",
                             os.environ.get("CONUS_CHANNEL_GEOMETRY_URL",
                                            "https://conus-channel-geometry.onrender.com"))

# Columns that are codes, not numbers: keep them as text so leading zeros survive.
_TEXT_COLUMNS = ["site_no", "station_nm", "reachcode", "state", "huc2", "huc8"]
_RETRY_STATUS = {502, 503, 504}          # the server is starting up or restarting


class ChannelGeometryError(Exception):
    """The API could not answer the request. The message explains why."""


class TooManyRecords(ChannelGeometryError):
    """The area has more records than one download allows.

    Attributes: ``records`` (how many matched), ``limit`` (the limit for this format).
    """
    def __init__(self, message: str, records: Optional[int] = None,
                 limit: Optional[int] = None):
        super().__init__(message)
        self.records, self.limit = records, limit


def get_channel_geometry(
    dataset: str = "reach",
    *,
    comids: Optional[Iterable[int]] = None,
    site_nos: Optional[Iterable[str]] = None,
    state: Optional[str] = None,
    huc2: Optional[str] = None,
    huc8: Optional[str] = None,
    polygon=None,
    conus: bool = False,
    geometry: bool = False,
    base_url: str = DEFAULT_URL,
    timeout: float = 600,
    retries: int = 3,
):
    """Download channel geometry for an area, as a table or a map layer.

    Choose **one** way to select the area:

    - ``comids``: NHDPlusV2.1 COMIDs (reaches), e.g. ``[18223451, 721640]``
    - ``site_nos``: USGS site numbers (gages), as text, e.g. ``["02465000"]``
    - ``state``: two-letter state code, e.g. ``"AL"``
    - ``huc2``: two-digit HUC2 region, e.g. ``"03"``
    - ``huc8``: eight-digit HUC8 watershed, e.g. ``"03160112"``
    - ``polygon``: a shapely geometry (longitude/latitude), a GeoDataFrame or GeoSeries
      in any coordinate system, or a GeoJSON geometry dictionary
    - ``conus=True``: everything (gages only; for all reaches use the Zenodo dataset)

    Parameters
    ----------
    dataset : "reach" or "gage"
        River reaches (default) or USGS gages. Passing ``site_nos`` selects gages.
    geometry : bool
        False (default): return a pandas DataFrame with the values only, up to
        500,000 records. True: return a GeoDataFrame with the reach lines or gage
        points (needs geopandas), up to 50,000 records.
    base_url : str
        The API address. Set the ``HYDROGEOMKIT_URL`` environment variable
        to change the default.
    timeout : float
        Seconds to wait for a response. Large areas can take a minute or more.
    retries : int
        How many times to retry if the server is starting up or restarting.

    Returns
    -------
    pandas.DataFrame, or geopandas.GeoDataFrame if ``geometry=True``.
    Columns: bnk_width, bnk_depth, mf_width, mf_depth (meters), plus IDs, state,
    HUC codes, stream order, and drainage area. Records without a prediction have
    empty (NaN) width and depth.

    Raises
    ------
    TooManyRecords
        The area is too big for one download. Try a smaller area, or
        ``geometry=False`` for the values only.
    ChannelGeometryError
        Anything else the API could not do, with the reason.
    """
    if site_nos is not None:
        dataset = "gage"
    dataset = dataset.lower()
    if dataset not in ("reach", "gage"):
        raise ValueError('dataset must be "reach" or "gage"')

    chosen = {k: v for k, v in dict(comids=comids, site_nos=site_nos, state=state,
                                     huc2=huc2, huc8=huc8, polygon=polygon).items()
              if v is not None}
    if conus:
        chosen["conus"] = True
    if len(chosen) != 1:
        raise ValueError("Choose exactly one of: comids, site_nos, state, huc2, huc8, "
                         f"polygon, conus=True (got {sorted(chosen) or 'none'})")
    (kind, value), = chosen.items()
    if kind == "comids" and dataset == "gage":
        raise ValueError("comids select reaches; use site_nos for gages")

    fmt = "geojson" if geometry else "csv"
    body = {"dataset": dataset, "format": fmt}
    if kind in ("comids", "site_nos"):
        ids = [str(v).strip() for v in _as_list(value)]
        if not ids:
            raise ValueError(f"{kind} is empty")
        body.update(request_type="ids", ids=ids)
    elif kind == "state":
        body.update(request_type="state", state=str(value).upper())
    elif kind == "huc2":
        body.update(request_type="huc2", huc2=str(value).zfill(2))
    elif kind == "huc8":
        body.update(request_type="huc8", huc8=str(value).zfill(8))
    elif kind == "polygon":
        body.update(request_type="polygon", polygon=_polygon_geojson(value))
    else:
        body.update(request_type="conus")

    r = _post(f"{base_url.rstrip('/')}/extract", body, timeout, retries)
    return _read_geojson(r.content) if geometry else _read_csv(r.text)


def status(base_url: str = DEFAULT_URL, timeout: float = 120) -> dict:
    """Number of reaches and gages the API serves, and where its data comes from."""
    r = requests.get(f"{base_url.rstrip('/')}/status", timeout=timeout)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- helpers
def _as_list(v):
    if isinstance(v, (str, int)):
        return [v]
    return list(v)


def _polygon_geojson(poly) -> dict:
    """Accept a GeoJSON dict, a shapely geometry, or a GeoDataFrame/GeoSeries."""
    if isinstance(poly, dict):
        return poly.get("geometry", poly) if poly.get("type") == "Feature" else poly
    if hasattr(poly, "to_crs"):                  # GeoDataFrame or GeoSeries
        if poly.crs is not None:
            poly = poly.to_crs(4326)
        geom = poly.union_all() if hasattr(poly, "union_all") else poly.unary_union
        return json.loads(json.dumps(geom.__geo_interface__))
    if hasattr(poly, "__geo_interface__"):
        return json.loads(json.dumps(poly.__geo_interface__))
    raise TypeError("polygon must be a GeoJSON dict, a shapely geometry, "
                    "or a GeoDataFrame/GeoSeries")


def _post(url: str, body: dict, timeout: float, retries: int) -> requests.Response:
    delay = 5
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, json=body, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout):
            if attempt == retries:
                raise ChannelGeometryError(
                    f"Could not reach the API at {url}. It may be starting up; "
                    "try again in a minute.") from None
            time.sleep(delay); delay *= 2
            continue
        if r.status_code in _RETRY_STATUS and attempt < retries:
            time.sleep(delay); delay *= 2
            continue
        if r.ok:
            return r
        _raise_for(r)
    _raise_for(r)


def _raise_for(r: requests.Response):
    detail = None
    try:
        detail = r.json().get("detail")
    except ValueError:
        pass
    if isinstance(detail, dict):
        msg = detail.get("message") or str(detail)
    elif isinstance(detail, list):              # validation errors
        msg = "; ".join(d.get("msg", str(d)) for d in detail)
    else:
        msg = detail or f"The API answered with error {r.status_code}."
    if r.status_code == 413:
        msg = msg.replace("Choose CSV to get", "Use geometry=False to get")
        d = detail if isinstance(detail, dict) else {}
        raise TooManyRecords(msg, d.get("records"), d.get("limit"))
    if r.status_code == 404:
        raise ChannelGeometryError("Nothing matched the request. Check the IDs or codes.")
    raise ChannelGeometryError(f"{msg} (HTTP {r.status_code})")


def _read_csv(text: str) -> pd.DataFrame:
    header = text.split("\n", 1)[0].split(",")
    dtype = {c: str for c in _TEXT_COLUMNS if c in header}
    return pd.read_csv(io.StringIO(text), dtype=dtype)


def _read_geojson(content: bytes):
    try:
        import geopandas as gpd
    except ImportError:
        raise ImportError("geometry=True needs geopandas: "
                          "pip install geopandas") from None
    gdf = gpd.read_file(io.BytesIO(content))
    for c in _TEXT_COLUMNS:
        if c in gdf.columns:
            gdf[c] = gdf[c].astype("string")
    if gdf.crs is None:
        gdf = gdf.set_crs(4269)
    return gdf
