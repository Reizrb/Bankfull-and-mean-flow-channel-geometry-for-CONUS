"""
One-time data preparation for the Channel Geometry API.

Turns the Zenodo release files into the Parquet files the API reads:
    gage  -> gages.parquet    (from the USGS gages CSV)
    reach -> reaches.parquet  (from the stream reaches shapefile, read in chunks)

Both outputs share one schema convention:
    id column          site_no (gage, text, leading zeros kept) | comid (reach, integer)
    region tags        state, huc2, huc8   (huc codes come from the 14-digit REACHCODE)
    geometry           geom_wkb (WKB) + minx, miny, maxx, maxy (bounding box)
    attributes         bnk_width, bnk_depth, mf_width, mf_depth (names as in the release)
                       + stream_order, tot_da_sqkm for reaches

Run:  python prepare_data.py gage     -> builds gages.parquet
      python prepare_data.py reach    -> builds reaches.parquet (takes a while)
"""
from pathlib import Path

import numpy as np
import pandas as pd

CRS = "EPSG:4269"         # NAD83, the NHDPlusV2.1 CRS
SENTINEL = -999999        # missing-value code used in the release
GEOM_ATTRS = ["bnk_width", "bnk_depth", "mf_width", "mf_depth"]

# ---------------------------------------------------------------- gage inputs
GAGE_CSV = "Bankfull_Meanflow_CONUS_USGS_Gages.csv"

# ---------------------------------------------------------------- reach inputs
# Point these at the Zenodo reach files on your machine.
REACH_SHP = "Bankfull_Meanflow_CONUS_Stream_Reaches.shp"   # line geometry, one row per reach
STATES_SHP = "cb_2023_us_state_500k.shp"    # Census state boundaries, for the state tag
CHUNK = 250_000                              # reaches read at a time (keeps memory low)


def _clean_sentinels(df, cols):
    for c in cols:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
            df.loc[df[c] <= SENTINEL + 1, c] = np.nan
    return df


def _huc_from_reachcode(df):
    rc = df["reachcode"].astype("string").str.zfill(14)
    df["reachcode"] = rc
    df["huc8"] = rc.str[:8]
    df["huc2"] = rc.str[:2]
    return df


def _add_wkb_and_bbox(df, geoms):
    """geoms: shapely array (may contain None). Stores WKB + bbox columns."""
    import shapely
    geoms = np.asarray(geoms, dtype=object)
    df["geom_wkb"] = shapely.to_wkb(geoms)          # None stays None
    b = shapely.bounds(geoms)                        # NaN for None
    df["minx"], df["miny"], df["maxx"], df["maxy"] = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    return df


# ---------------------------------------------------------------- gage
def build_gages():
    import shapely

    df = pd.read_csv(GAGE_CSV, dtype={"REACHCODE": str, "SOURCE_FEA": str})
    df = df.rename(columns={
        "SOURCE_FEA": "site_no", "FLComID": "comid", "REACHCODE": "reachcode",
        "STATION_NM": "station_nm", "STATE": "state", "DASqKm": "da_sqkm",
        "LatSite": "lat", "LonSite": "lon",
    })
    df = df.dropna(subset=["site_no"])
    df["site_no"] = df["site_no"].str.strip()
    df["comid"] = pd.to_numeric(df["comid"], errors="coerce").astype("Int64")
    df = _clean_sentinels(df, ["da_sqkm"] + GEOM_ATTRS)
    df = _huc_from_reachcode(df)
    df["state"] = df["state"].str.upper()

    has_xy = df["lat"].notna() & df["lon"].notna()
    geoms = [shapely.Point(x, y) if ok else None
             for x, y, ok in zip(df["lon"], df["lat"], has_xy)]
    df = _add_wkb_and_bbox(df, geoms)

    cols = ["site_no", "station_nm", "comid", "reachcode", "state", "huc2", "huc8",
            "da_sqkm", "lat", "lon"] + GEOM_ATTRS + \
           ["geom_wkb", "minx", "miny", "maxx", "maxy"]
    df = df[cols].sort_values("site_no").reset_index(drop=True)
    df.to_parquet("gages.parquet", index=False)

    print(f"wrote gages.parquet: {len(df):,} gages")
    print(f"  without coordinates (kept, not findable by polygon): {(~has_xy).sum():,}")
    print(f"  without a state tag: {df['state'].isna().sum():,}")
    print(f"  without channel geometry values: {df['bnk_width'].isna().sum():,}")
    print(f"  states: {', '.join(sorted(df['state'].dropna().unique()))}")


# ---------------------------------------------------------------- reach
REACH_COLS = ["comid", "reachcode", "state", "huc2", "huc8", "stream_order",
              "tot_da_sqkm"] + GEOM_ATTRS + ["geom_wkb", "minx", "miny", "maxx", "maxy"]


def _prep_reach_chunk(gdf, states):
    import geopandas as gpd

    gdf.columns = [c if c == "geometry" else c.lower() for c in gdf.columns]
    gdf = gdf.rename(columns={"flcomid": "comid", "streamorde": "stream_order",
                              "totdasqkm": "tot_da_sqkm"})
    missing = [c for c in ["comid", "reachcode"] + GEOM_ATTRS if c not in gdf]
    if missing:
        raise SystemExit(f"Missing columns {missing}. Found: {list(gdf.columns)}")
    for c in ["stream_order", "tot_da_sqkm"]:
        if c not in gdf:
            gdf[c] = np.nan
    gdf = gdf.to_crs(CRS)
    # NHDPlus lines carry Z (and M) values that the API never uses; keep x/y only
    import shapely
    gdf = gdf.set_geometry(shapely.force_2d(gdf.geometry.values), crs=CRS)
    gdf["comid"] = pd.to_numeric(gdf["comid"]).astype("int64")
    gdf["stream_order"] = pd.to_numeric(gdf["stream_order"], errors="coerce").astype("Int64")
    gdf = _clean_sentinels(gdf, GEOM_ATTRS + ["tot_da_sqkm"])
    gdf = _huc_from_reachcode(gdf)

    # state tag: spatial join of each reach's representative point
    pts = gpd.GeoDataFrame({"_i": np.arange(len(gdf))},
                           geometry=gdf.representative_point().values, crs=CRS)
    tagged = gpd.sjoin(pts, states, how="left", predicate="within")
    tagged = tagged.drop_duplicates("_i").set_index("_i")["STUSPS"]
    state = tagged.reindex(np.arange(len(gdf)))
    # reaches on the coast or a border can fall just outside the generalized state
    # outlines; give them the nearest state (within ~5 km) instead of leaving it empty
    miss = state.isna().values
    if miss.any():
        far = pts[miss].to_crs("EPSG:5070")
        near = gpd.sjoin_nearest(far, states.to_crs("EPSG:5070"), how="left",
                                 max_distance=5000)
        near = near.drop_duplicates("_i").set_index("_i")["STUSPS"]
        state.loc[near.index] = near.values
    gdf["state"] = state.values

    df = pd.DataFrame(gdf.drop(columns="geometry"))
    for c in ["reachcode", "state", "huc2", "huc8"]:   # fixed text type in every chunk
        df[c] = df[c].astype("string")
    df = _add_wkb_and_bbox(df, gdf.geometry.values)
    return df[REACH_COLS]


def build_reaches():
    import geopandas as gpd
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pyogrio

    info = pyogrio.read_info(REACH_SHP)
    total = info["features"]
    if info["crs"] is None:
        raise SystemExit("Reach shapefile has no .prj; cannot determine its CRS.")
    states = gpd.read_file(STATES_SHP).to_crs(CRS)[["STUSPS", "geometry"]]

    out = "reaches.parquet"
    writer, schema, n_done, no_state = None, None, 0, 0
    try:
        for start in range(0, total, CHUNK):
            gdf = gpd.read_file(REACH_SHP, skip_features=start, max_features=CHUNK)
            df = _prep_reach_chunk(gdf, states)
            if schema is None:
                table = pa.Table.from_pandas(df, preserve_index=False)
                schema = table.schema
                writer = pq.ParquetWriter(out, schema, compression="zstd")
            else:
                table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
            writer.write_table(table)
            n_done += len(df)
            no_state += int(df["state"].isna().sum())
            print(f"  {n_done:,} / {total:,} reaches", flush=True)
    finally:
        if writer is not None:
            writer.close()

    size_mb = Path(out).stat().st_size / 1e6
    print(f"wrote {out}: {n_done:,} reaches, {size_mb:,.0f} MB")
    print(f"  without a state tag (more than 5 km outside any state): {no_state:,}")


if __name__ == "__main__":
    import sys
    choice = sys.argv[1] if len(sys.argv) > 1 else ""
    if choice not in ("gage", "reach"):
        raise SystemExit("Usage: python prepare_data.py gage   OR   python prepare_data.py reach")
    {"gage": build_gages, "reach": build_reaches}[choice]()
