"""
Checks every request type against whatever data is in the folder
(the fake sample reaches OR your real reaches.parquet, plus gages.parquet).
Test values (a COMID, a state, a HUC8, a small box) are picked from the data itself.

Run:  python test_api.py
"""
import io, zipfile, tempfile
from pathlib import Path
import duckdb
import geopandas as gpd
from shapely.geometry import box, mapping
from fastapi.testclient import TestClient
from app import app, DATASETS, MAX_SYNC_ROWS, _available

c = TestClient(app)
ok_count, fail_count = 0, 0


def check(label, cond, detail=""):
    global ok_count, fail_count
    ok_count += bool(cond); fail_count += (not cond)
    print(f"{'OK  ' if cond else 'FAIL'}  {label}  {detail}")


def rows(r):
    return len(r.text.strip().splitlines()) - 1


def pick(ds):
    """Pull real test values out of the parquet file."""
    p = DATASETS[ds]["path"]; idc = DATASETS[ds]["id_col"]
    q = duckdb.sql(f"""SELECT {idc}, state, huc2, huc8, minx, miny, maxx, maxy
                       FROM read_parquet('{p}')
                       WHERE state IS NOT NULL AND minx IS NOT NULL LIMIT 1""").fetchone()
    ids = [str(r[0]) for r in duckdb.sql(
        f"SELECT {idc} FROM read_parquet('{p}') LIMIT 3").fetchall()]
    x0, y0, x1, y1 = q[4:]
    pad = 0.05
    return dict(ids=ids, state=q[1], huc2=q[2], huc8=q[3],
                box=box(x0 - pad, y0 - pad, x1 + pad, y1 + pad))


print("health:", c.get("/health").json(), "\n")

for ds in ["reach", "gage"]:
    if not _available(DATASETS[ds]):
        print(f"(skipping {ds}: file not built)\n"); continue
    v = pick(ds)
    name = "gages" if ds == "gage" else "reaches"
    print(f"--- {ds}  (test values: state={v['state']}, huc8={v['huc8']}, ids={v['ids']})")

    def post(body):
        return c.post("/extract", json={"dataset": ds, **body})

    r = post({"request_type": "ids", "ids": v["ids"], "format": "csv"})
    check("ids -> csv", r.status_code == 200 and rows(r) == len(v["ids"]), f"rows={rows(r)}")

    r = post({"request_type": "huc8", "huc8": v["huc8"], "format": "geojson"})
    check("huc8 -> geojson", r.status_code == 200,
          f"features={len(r.json()['features']) if r.status_code == 200 else r.status_code}")

    r = post({"request_type": "polygon", "polygon": mapping(v["box"]), "format": "csv"})
    check("drawn polygon -> csv", r.status_code == 200, f"rows={rows(r) if r.status_code == 200 else r.status_code}")

    r = post({"request_type": "ids", "ids": v["ids"], "format": "shapefile"})
    parts = sorted(x.split('.')[-1] for x in zipfile.ZipFile(io.BytesIO(r.content)).namelist()) \
        if r.status_code == 200 else r.status_code
    check("ids -> shapefile zip", r.status_code == 200 and "shp" in parts, f"parts={parts}")

    with tempfile.TemporaryDirectory() as td:
        shp = Path(td) / "mask.shp"
        gpd.GeoDataFrame(geometry=[v["box"]], crs="EPSG:4269").to_file(shp)
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w") as zf:
            for f in Path(td).glob("mask.*"):
                zf.write(f, f.name)
        zbuf.seek(0)
        r = c.post("/extract/shapefile", files={"file": ("mask.zip", zbuf, "application/zip")},
                   data={"format": "geojson", "dataset": ds})
    check("uploaded shapefile -> geojson", r.status_code == 200)

    # state / huc2 / conus can be bigger than the sync limit with real reach data
    for rt, extra in [("state", {"state": v["state"]}), ("huc2", {"huc2": v["huc2"]}),
                      ("conus", {})]:
        r = post({"request_type": rt, "format": "csv", **extra})
        good = r.status_code == 200 or r.status_code == 413
        note = f"rows={rows(r)}" if r.status_code == 200 else f"413: over {MAX_SYNC_ROWS:,} limit (expected for big areas)"
        check(f"{rt} -> csv", good, note)

    check("filename", post({"request_type": "ids", "ids": v["ids"], "format": "csv"})
          .headers["content-disposition"].endswith(f"{name}.csv"))
    print()

print("--- guardrails")
check("bad format -> 400", c.post("/extract", json={"request_type": "state", "state": "AL", "format": "kml"}).status_code == 400)
check("no match -> 404", c.post("/extract", json={"request_type": "state", "state": "ZZ", "format": "csv"}).status_code == 404)
check("missing param -> 400", c.post("/extract", json={"request_type": "state", "format": "csv"}).status_code == 400)
check("text id for reach -> 400", c.post("/extract", json={"request_type": "ids", "ids": ["abc"]}).status_code == 400)
check("unknown dataset -> 400", c.post("/extract", json={"dataset": "lake", "request_type": "conus"}).status_code == 400)

print(f"\n{ok_count} passed, {fail_count} failed")
