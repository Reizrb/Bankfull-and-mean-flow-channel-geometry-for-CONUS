"""
Channel Geometry API
--------------------
Serves ML-derived channel geometry for NHDPlus reaches and USGS gages
(Zarrabi et al., WRR, doi:10.1029/2024WR037997; data doi:10.5281/zenodo.19208847).

Two interfaces are supported by this backend:
  1. Menu interface -> POST /extract      (conus | ids | state | huc2 | huc8 | polygon)
     dataset = "reach" (default, ids are COMIDs) | "gage" (ids are USGS site numbers)
  2. Map interface  -> POST /extract      (request_type="polygon", drawn GeoJSON)
                    -> POST /extract/shapefile   (uploaded zipped shapefile polygon)

Every response is a downloadable file in the format the user chose:
  format = "csv" | "shapefile" | "geojson"

Design notes
------------
* Region filters (state/huc2/huc8) and comid filters are plain indexed WHERE
  clauses in DuckDB against the Parquet file -> fast at 2.7M rows, no spatial DB.
* Polygon queries use a two-step filter: DuckDB bbox pre-filter (cheap, uses the
  precomputed minx/miny/maxx/maxy columns) then a precise shapely intersection on
  the small candidate set. User polygons are reprojected to DATASET_CRS first.
* A synchronous size guard (MAX_SYNC_ROWS) protects against someone pulling all
  of CONUS in one request. For CONUS / very large regions you'll want prebuilt
  static downloads or an async job queue (see the guard for where to branch).
"""
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from shapely import from_wkb
from shapely.geometry import shape

# ------------------------------------------------------------------ config
HERE = Path(__file__).parent

# Where the data files live. By default the API uses local copies if they are in
# this folder, and otherwise reads them straight from the Hugging Face dataset.
# Set CG_DATA_URL to another base address (e.g. an S3 bucket) to switch storage.
REMOTE_BASE = os.environ.get(
    "CG_DATA_URL",
    "https://huggingface.co/datasets/Reizrb/bankfull-meanflow-conus/resolve/main")


def _data_path(filename: str) -> str:
    local = HERE / filename
    if local.exists() and not os.environ.get("CG_DATA_URL"):
        return str(local)
    return f"{REMOTE_BASE.rstrip('/')}/{filename}"

DATASET_CRS = "EPSG:4269"      # NAD83, the NHDPlusV2.1 CRS (both files are built in it)
MAX_SYNC_ROWS = 50_000         # above this, refuse sync return (use prebuilt/async)
GEOM_ATTRS = ["bnk_width", "bnk_depth", "mf_width", "mf_depth"]

# One entry per dataset. `id_col` is what request_type="ids" matches against.
DATASETS = {
    "reach": {
        "path": _data_path("reaches.parquet"),
        "id_col": "comid", "id_type": int,
        "cols": ["comid", "reachcode", "state", "huc2", "huc8", "stream_order",
                 "tot_da_sqkm"] + GEOM_ATTRS,
    },
    "gage": {
        "path": _data_path("gages.parquet"),
        "id_col": "site_no", "id_type": str,   # text, so leading zeros survive
        "cols": ["site_no", "station_nm", "comid", "reachcode", "state", "huc2",
                 "huc8", "da_sqkm", "lat", "lon"] + GEOM_ATTRS,
    },
}


def _ds(name: str) -> dict:
    ds = DATASETS.get(name.lower())
    if ds is None:
        raise HTTPException(400, f"Unknown dataset '{name}'. Use reach or gage.")
    if not _available(ds):
        raise HTTPException(503, f"The {name} dataset is not available on this server.")
    return ds


def _available(ds: dict) -> bool:
    p = ds["path"]
    return p.startswith("http") or Path(p).exists()

app = FastAPI(title="Channel Geometry API", version="0.2.0")
# allow the browser map/menu frontend to call this API
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


def con():
    c = duckdb.connect()
    c.execute("PRAGMA threads=4")
    return c


# ------------------------------------------------------------------ request model
class ExtractRequest(BaseModel):
    dataset: str = Field("reach", description="reach | gage")
    request_type: str = Field(..., description="conus | ids | comids | state | huc2 | huc8 | polygon")
    format: str = Field("csv", description="csv | shapefile | geojson")
    # one of these is used depending on request_type:
    ids: list[str] | None = Field(None, description="COMIDs (reach) or USGS site numbers (gage)")
    comids: list[int] | None = Field(None, description="kept for older clients; same as ids")
    state: str | None = None
    huc2: str | None = None
    huc8: str | None = None
    polygon: dict | None = None   # GeoJSON geometry (from the drawn polygon), WGS84


# ------------------------------------------------------------------ query helpers
def _fetch_by_filter(ds: dict, where_sql: str, params: list) -> gpd.GeoDataFrame:
    """Run an attribute/id filter and return a GeoDataFrame."""
    cols = ", ".join(ds["cols"] + ["geom_wkb"])
    sql = f"SELECT {cols} FROM read_parquet('{ds['path']}')"
    if where_sql:
        sql += f" WHERE {where_sql}"
    df = con().execute(sql, params).fetch_df()
    return _to_gdf(df)


def _fetch_by_polygon(ds: dict, geom) -> gpd.GeoDataFrame:
    """Two-step: DuckDB bbox pre-filter, then precise shapely intersection.
    Rows with no geometry have NULL bbox columns, so they drop out here."""
    minx, miny, maxx, maxy = geom.bounds
    cols = ", ".join(ds["cols"] + ["geom_wkb"])
    # bbox overlap test using the precomputed corner columns
    sql = (f"SELECT {cols} FROM read_parquet('{ds['path']}') "
           f"WHERE minx <= ? AND maxx >= ? AND miny <= ? AND maxy >= ?")
    df = con().execute(sql, [maxx, minx, maxy, miny]).fetch_df()
    gdf = _to_gdf(df)
    if gdf.empty:
        return gdf
    return gdf[gdf.intersects(geom)].reset_index(drop=True)


def _to_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    # DuckDB returns BLOB as bytearray; shapely.from_wkb wants bytes.
    # Some gages have no coordinates -> NULL blob -> empty geometry.
    geom = from_wkb([None if b is None or b is pd.NA else bytes(b)
                     for b in df.pop("geom_wkb").values])
    return gpd.GeoDataFrame(df, geometry=geom, crs=DATASET_CRS)


def _user_polygon_to_dataset_crs(geojson_geom: dict):
    """Drawn polygons arrive as GeoJSON in WGS84; reproject to the dataset CRS."""
    g = shape(geojson_geom)
    s = gpd.GeoSeries([g], crs="EPSG:4326").to_crs(DATASET_CRS)
    return s.iloc[0]


# ------------------------------------------------------------------ formatting
def _stream(gdf: gpd.GeoDataFrame, fmt: str, name: str = "reaches") -> StreamingResponse:
    if len(gdf) > MAX_SYNC_ROWS:
        # ---- branch point: CONUS / huge regions go to prebuilt files or async here
        raise HTTPException(
            status_code=413,
            detail=(f"{len(gdf)} records exceeds the {MAX_SYNC_ROWS} sync limit. "
                    "Use a prebuilt regional download or the async export endpoint."))
    fmt = fmt.lower()
    if fmt == "csv":
        out = gdf.copy()
        out["geometry_wkt"] = out.geometry.to_wkt()   # keep geometry, as WKT
        buf = io.StringIO()
        out.drop(columns="geometry").to_csv(buf, index=False)
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode()), media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={name}.csv"})

    if fmt == "geojson":
        return StreamingResponse(
            io.BytesIO(gdf.to_json().encode()), media_type="application/geo+json",
            headers={"Content-Disposition": f"attachment; filename={name}.geojson"})

    if fmt == "shapefile":
        with tempfile.TemporaryDirectory() as td:
            shp = Path(td) / f"{name}.shp"
            gdf.to_file(shp, driver="ESRI Shapefile")  # writes .shp/.shx/.dbf/.prj
            zbuf = io.BytesIO()
            with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
                for f in Path(td).glob(f"{name}.*"):
                    z.write(f, f.name)
            zbuf.seek(0)
            return StreamingResponse(
                zbuf, media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={name}.zip"})

    raise HTTPException(400, f"Unknown format '{fmt}'. Use csv, shapefile, or geojson.")


# ------------------------------------------------------------------ endpoints
@app.post("/extract")
def extract(req: ExtractRequest):
    ds = _ds(req.dataset)
    _check_format(req.format)
    rt = req.request_type.lower()
    if rt == "conus":
        gdf = _fetch_by_filter(ds, "", [])
    elif rt in ("ids", "comids"):
        raw = req.ids or ([str(c) for c in req.comids] if req.comids else None)
        if not raw:
            raise HTTPException(400, "ids is required for request_type=ids")
        try:
            ids = [ds["id_type"](str(i).strip()) for i in raw]
        except ValueError:
            raise HTTPException(400, f"ids for the {req.dataset} dataset must be "
                                     f"{ds['id_type'].__name__} values")
        placeholders = ", ".join("?" * len(ids))
        gdf = _fetch_by_filter(ds, f"{ds['id_col']} IN ({placeholders})", ids)
    elif rt == "state":
        if not req.state:
            raise HTTPException(400, "state is required for request_type=state")
        gdf = _fetch_by_filter(ds, "state = ?", [req.state.upper()])
    elif rt == "huc2":
        if not req.huc2:
            raise HTTPException(400, "huc2 is required for request_type=huc2")
        gdf = _fetch_by_filter(ds, "huc2 = ?", [req.huc2.zfill(2)])
    elif rt == "huc8":
        if not req.huc8:
            raise HTTPException(400, "huc8 is required for request_type=huc8")
        gdf = _fetch_by_filter(ds, "huc8 = ?", [req.huc8.zfill(8)])
    elif rt == "polygon":
        if not req.polygon:
            raise HTTPException(400, "polygon (GeoJSON) is required for request_type=polygon")
        geom = _user_polygon_to_dataset_crs(req.polygon)
        gdf = _fetch_by_polygon(ds, geom)
    else:
        raise HTTPException(400, f"Unknown request_type '{req.request_type}'")

    if gdf.empty:
        raise HTTPException(404, "No records matched the query.")
    return _stream(gdf, req.format, _outname(req.dataset))


def _check_format(fmt: str):
    if fmt.lower() not in ("csv", "geojson", "shapefile"):
        raise HTTPException(400, f"Unknown format '{fmt}'. Use csv, shapefile, or geojson.")


def _outname(dataset: str) -> str:
    return "gages" if dataset.lower() == "gage" else "reaches"


@app.post("/extract/shapefile")
async def extract_shapefile(
    file: UploadFile = File(..., description="zipped shapefile (.shp/.shx/.dbf/.prj)"),
    format: str = Form("csv"),
    dataset: str = Form("reach"),
):
    """Map interface: uploaded polygon shapefile. Reprojects to dataset CRS,
    then intersects. Accepts a .zip containing the shapefile parts."""
    ds = _ds(dataset)
    _check_format(format)
    raw = await file.read()
    with tempfile.TemporaryDirectory() as td:
        zpath = Path(td) / "upload.zip"
        zpath.write_bytes(raw)
        try:
            with zipfile.ZipFile(zpath) as z:
                z.extractall(td)
        except zipfile.BadZipFile:
            raise HTTPException(400, "Upload must be a .zip containing the shapefile parts.")
        shp = next(Path(td).rglob("*.shp"), None)
        if shp is None:
            raise HTTPException(400, "No .shp found in the uploaded zip.")
        poly = gpd.read_file(shp)          # reads .prj automatically
        if poly.crs is None:
            raise HTTPException(400, "Shapefile has no .prj / CRS; cannot reproject.")
        poly = poly.to_crs(DATASET_CRS)    # <- the step that prevents silent empty results
        geom = poly.union_all()            # merge all polygon features into one mask

    gdf = _fetch_by_polygon(ds, geom)
    if gdf.empty:
        raise HTTPException(404, "No records intersected the uploaded polygon.")
    return _stream(gdf, format, _outname(dataset))


@app.get("/health")
def health():
    counts = {}
    for name, ds in DATASETS.items():
        if _available(ds):
            counts[name] = con().execute(
                f"SELECT count(*) FROM read_parquet('{ds['path']}')").fetchone()[0]
        else:
            counts[name] = "not loaded"
    source = "local files" if not DATASETS["reach"]["path"].startswith("http") else REMOTE_BASE
    return {"status": "ok", "records": counts, "data_source": source,
            "dataset_crs": DATASET_CRS}
