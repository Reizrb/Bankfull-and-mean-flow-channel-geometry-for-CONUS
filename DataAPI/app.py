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
import shutil
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
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
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
MAX_SYNC_ROWS = 50_000         # shapefile / GeoJSON (with line shapes): records per request
MAX_CSV_ROWS = 500_000         # CSV (numbers only, no line shapes): covers every state and HUC2


def _limit(fmt: str) -> int:
    return MAX_CSV_ROWS if (fmt or "csv").lower() == "csv" else MAX_SYNC_ROWS
ZENODO_URL = "https://zenodo.org/records/19208847"


class TooBig(Exception):
    """Raised before any geometry is loaded when a request is over the format's limit."""
    def __init__(self, n, huc2s, limit, fmt):
        self.n, self.huc2s, self.limit, self.fmt = n, huc2s, limit, fmt
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


STATIC = HERE / "static"
if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def home():
    """The web page (menu + map) for people who don't want to write code."""
    page = STATIC / "index.html"
    if page.exists():
        return FileResponse(page)
    return {"message": "Channel Geometry API. See /docs."}


# One shared DuckDB database for the whole app, so what it learns about the data
# files (their layout, which parts hold which HUCs) is cached between requests
# instead of being downloaded again from Hugging Face every time.
_DB = duckdb.connect()
_DB.execute("PRAGMA threads=1")      # the free server has a tenth of a CPU; leave room for /health
_DB.execute("SET memory_limit = '256MB'")        # the free server has 512 MB in total
_DB.execute(f"SET temp_directory = '{tempfile.gettempdir()}/duckdb_spill'")
for _setting in ("SET enable_object_cache = true",
                 "SET enable_http_metadata_cache = true"):
    try:
        _DB.execute(_setting)
    except Exception:          # older/newer DuckDB versions may not have both
        pass


def _load_spatial(db):
    """DuckDB's spatial extension: geometry tests and GeoJSON/shapefile writing inside
    DuckDB, so large results never have to be held in Python memory."""
    try:
        db.execute("LOAD spatial"); return
    except Exception:
        pass
    try:                                   # pip package duckdb-extension-spatial
        import duckdb_extension_spatial as pkg
        ext = next(Path(pkg.__file__).parent.rglob("spatial.duckdb_extension"))
        db.execute(f"LOAD '{ext}'"); return
    except Exception:
        pass
    db.execute("INSTALL spatial"); db.execute("LOAD spatial")


_load_spatial(_DB)


def con():
    """A cursor on the shared database (safe to use from several requests at once)."""
    return _DB.cursor()


# ------------------------------------------------------------------ request model
class ExtractRequest(BaseModel):
    dataset: str = Field("reach", description="reach | gage")
    request_type: str = Field(..., description="conus | ids | comids | state | huc2 | huc8 | polygon")
    format: str = Field("csv", description="csv | shapefile | geojson")
    # one of these is used depending on request_type:
    ids: list[int | str] | None = Field(None, description="COMIDs (reach) or USGS site numbers (gage, as text)")
    comids: list[int] | None = Field(None, description="kept for older clients; same as ids")
    state: str | None = None
    huc2: str | None = None
    huc8: str | None = None
    polygon: dict | None = None   # GeoJSON geometry (from the drawn polygon), WGS84


# ------------------------------------------------------------------ query helpers
def _check_size(ds: dict, where_sql: str, params: list, fmt: str = "csv"):
    """Count matches first (cheap: no geometry is read) and stop oversized requests
    before they use up the server's memory."""
    where = f" WHERE {where_sql}" if where_sql else ""
    n, huc2s = con().execute(
        f"SELECT count(*), list(DISTINCT huc2 ORDER BY huc2) "
        f"FROM read_parquet('{ds['path']}'){where}", params).fetchone()
    if n > _limit(fmt):
        raise TooBig(n, [h for h in huc2s if h], _limit(fmt), fmt)


def _fetch_by_filter(ds: dict, where_sql: str, params: list, fmt: str = "csv") -> tuple:
    """Check the size, then return the query (WHERE clause + parameters) to export."""
    _check_size(ds, where_sql, params, fmt)
    return (where_sql, list(params))


def _fetch_by_polygon(ds: dict, geom, fmt: str = "csv") -> tuple:
    """Bounding-box pre-filter (cheap, uses the precomputed corner columns), then an
    exact intersection test, both done inside DuckDB."""
    minx, miny, maxx, maxy = geom.bounds
    bbox = "minx <= ? AND maxx >= ? AND miny <= ? AND maxy >= ?"
    bparams = [maxx, minx, maxy, miny]
    _check_size(ds, bbox, bparams, fmt)
    where = bbox + " AND ST_Intersects(ST_GeomFromWKB(geom_wkb), ST_GeomFromText(?))"
    return (where, bparams + [geom.wkt])


def _user_polygon_to_dataset_crs(geojson_geom: dict):
    """Drawn polygons arrive as GeoJSON in WGS84; reproject to the dataset CRS."""
    g = shape(geojson_geom)
    s = gpd.GeoSeries([g], crs="EPSG:4326").to_crs(DATASET_CRS)
    return s.iloc[0]


# ------------------------------------------------------------------ formatting
def _stream(ds: dict, query: tuple, fmt: str, name: str = "reaches"):
    """Write the result straight to a file with DuckDB (low memory), then send it."""
    where_sql, params = query
    fmt = fmt.lower()
    cols = ", ".join(ds["cols"])
    where = f" WHERE {where_sql}" if where_sql else ""
    src = f"FROM read_parquet('{ds['path']}'){where}"
    td = tempfile.mkdtemp(prefix="cg_")
    cleanup = BackgroundTask(shutil.rmtree, td, ignore_errors=True)
    try:
        if fmt == "csv":
            out = Path(td) / f"{name}.csv"
            n = con().execute(
                f"COPY (SELECT {cols} {src}) "
                f"TO '{out}' (FORMAT CSV, HEADER)", params).fetchone()[0]
            media = "text/csv"
        elif fmt == "geojson":
            out = Path(td) / f"{name}.geojson"
            n = con().execute(
                f"COPY (SELECT {cols}, ST_GeomFromWKB(geom_wkb) AS geom {src}) "
                f"TO '{out}' (FORMAT GDAL, DRIVER 'GeoJSON', SRS 'EPSG:4269', "
                f"LAYER_CREATION_OPTIONS 'COORDINATE_PRECISION=6')", params).fetchone()[0]
            media = "application/geo+json"
        elif fmt == "shapefile":
            shp_dir = Path(td) / "shp"; shp_dir.mkdir()
            n = con().execute(
                f"COPY (SELECT {cols}, ST_GeomFromWKB(geom_wkb) AS geom {src}) "
                f"TO '{shp_dir / (name + '.shp')}' (FORMAT GDAL, DRIVER 'ESRI Shapefile', "
                f"SRS 'EPSG:4269')", params).fetchone()[0]
            out = Path(td) / f"{name}.zip"
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                for f in shp_dir.glob(f"{name}.*"):
                    z.write(f, f.name)
            media = "application/zip"
        else:
            raise HTTPException(400, f"Unknown format '{fmt}'. Use csv, shapefile, or geojson.")
    except Exception:
        shutil.rmtree(td, ignore_errors=True)
        raise
    if not n:
        shutil.rmtree(td, ignore_errors=True)
        raise HTTPException(404, "No records matched the query.")
    return FileResponse(out, media_type=media, filename=out.name, background=cleanup)


# ------------------------------------------------------------------ endpoints
def _too_big(err: TooBig, what: str) -> HTTPException:
    """413 answer that tells the user where to get large areas instead."""
    msg = (f"{what} has {err.n:,} records, more than the {err.limit:,} this API returns "
           f"in one {err.fmt.upper() if err.fmt != 'shapefile' else 'shapefile'} download. ")
    if err.fmt.lower() != "csv" and err.n <= MAX_CSV_ROWS:
        msg += ("Choose CSV to get the width and depth values for this whole area "
                f"(up to {MAX_CSV_ROWS:,} records), or ask for a smaller area for line shapes.")
    else:
        msg += "Ask for a smaller area, or download the full dataset from Zenodo."
    return HTTPException(413, {"message": msg, "records": err.n, "limit": err.limit,
                               "full_dataset": ZENODO_URL})


@app.post("/extract")
def extract(req: ExtractRequest):
    try:
        return _extract(req)
    except TooBig as err:
        what = {"conus": "All of CONUS", "state": f"State {req.state}",
                "huc2": f"HUC2 {req.huc2}", "polygon": "This polygon"
                }.get(req.request_type.lower(), "This request")
        raise _too_big(err, what)


def _extract(req: ExtractRequest):
    ds = _ds(req.dataset)
    _check_format(req.format)
    rt = req.request_type.lower()
    if rt == "conus":
        gdf = _fetch_by_filter(ds, "", [], req.format)
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
        gdf = _fetch_by_filter(ds, f"{ds['id_col']} IN ({placeholders})", ids, req.format)
    elif rt == "state":
        if not req.state:
            raise HTTPException(400, "state is required for request_type=state")
        gdf = _fetch_by_filter(ds, "state = ?", [req.state.upper()], req.format)
    elif rt == "huc2":
        if not req.huc2:
            raise HTTPException(400, "huc2 is required for request_type=huc2")
        gdf = _fetch_by_filter(ds, "huc2 = ?", [req.huc2.zfill(2)], req.format)
    elif rt == "huc8":
        if not req.huc8:
            raise HTTPException(400, "huc8 is required for request_type=huc8")
        gdf = _fetch_by_filter(ds, "huc8 = ?", [req.huc8.zfill(8)], req.format)
    elif rt == "polygon":
        if not req.polygon:
            raise HTTPException(400, "polygon (GeoJSON) is required for request_type=polygon")
        geom = _user_polygon_to_dataset_crs(req.polygon)
        gdf = _fetch_by_polygon(ds, geom, req.format)
    else:
        raise HTTPException(400, f"Unknown request_type '{req.request_type}'")

    return _stream(ds, gdf, req.format, _outname(req.dataset))


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

    try:
        gdf = _fetch_by_polygon(ds, geom, format)
    except TooBig as err:
        raise _too_big(err, "This polygon")
    return _stream(ds, gdf, format, _outname(dataset))


_COUNTS: dict = {}


@app.get("/health")
async def health():
    """Fast check used by the host: answers immediately, without reading the data."""
    return {"status": "ok"}


@app.get("/status")
def status():
    """Record counts and data source (reads the file footers once, then cached)."""
    if not _COUNTS:
        for name, ds in DATASETS.items():
            if _available(ds):
                _COUNTS[name] = con().execute(
                    f"SELECT count(*) FROM read_parquet('{ds['path']}')").fetchone()[0]
            else:
                _COUNTS[name] = "not loaded"
    source = "local files" if not DATASETS["reach"]["path"].startswith("http") else REMOTE_BASE
    return {"status": "ok", "records": _COUNTS, "data_source": source,
            "dataset_crs": DATASET_CRS}
