"""
Generate a small synthetic REACH dataset so the API runs out of the box.
(The gage dataset is small enough to build for real: python prepare_data.py)

Your real dataset should follow the SAME schema and build steps:
  - one row per NHDPlus reach
  - a stable reach id column: `comid`
  - region-tag columns computed ONCE at build time: `state`, `huc2`, `huc8`
      * huc2 / huc8 come from NHDPlus VAA (or derive huc2 = huc8[:2])
      * state comes from a one-time spatial join against a state-boundary layer
  - the reach geometry stored as WKB in `geom_wkb`
  - a precomputed bounding box per reach: `minx, miny, maxx, maxy`
      * this is what makes polygon queries fast at 2.7M rows WITHOUT a spatial DB
  - your actual channel-geometry attributes (width, depth, etc.)

Save as GeoParquet/Parquet and point DATA_PATH at it. DuckDB reads it lazily
with predicate pushdown, so region/comid filters stay fast at continental scale.
"""
import numpy as np
import pandas as pd
from shapely.geometry import LineString
from shapely import to_wkb

RNG = np.random.default_rng(42)

# a few fake regions so every menu filter has something to hit
STATES = ["AL", "CO", "TX"]
# (state -> (huc2, [huc8s], lon/lat box to scatter reaches in)
REGIONS = {
    "AL": ("03", ["03150201", "03160203"], (-88.0, 32.0, -86.0, 34.0)),
    "CO": ("14", ["14010001", "14080101"], (-108.0, 38.0, -106.0, 40.0)),
    "TX": ("12", ["12040104", "12070101"], (-97.0, 29.0, -95.0, 31.0)),
}

rows = []
comid = 1000000
for state, (huc2, huc8s, (x0, y0, x1, y1)) in REGIONS.items():
    for huc8 in huc8s:
        for _ in range(40):  # 40 reaches per huc8
            comid += 1
            # a short 3-vertex reach line
            sx = RNG.uniform(x0, x1)
            sy = RNG.uniform(y0, y1)
            pts = [(sx, sy)]
            for _ in range(2):
                sx += RNG.uniform(-0.05, 0.05)
                sy += RNG.uniform(-0.05, 0.05)
                pts.append((sx, sy))
            line = LineString(pts)
            minx, miny, maxx, maxy = line.bounds
            rows.append({
                "comid": comid,
                "state": state,
                "reachcode": huc8 + f"{comid % 1000000:06d}",
                "huc2": huc2,
                "huc8": huc8,
                "stream_order": int(RNG.integers(1, 8)),
                "tot_da_sqkm": round(float(RNG.uniform(1, 5000)), 2),
                # --- your ML-derived channel geometry attributes go here ---
                "bnk_width": round(float(RNG.uniform(3, 120)), 2),
                "bnk_depth": round(float(RNG.uniform(0.3, 8.0)), 2),
                "mf_width": round(float(RNG.uniform(2, 90)), 2),
                "mf_depth": round(float(RNG.uniform(0.2, 5.0)), 2),
                # --- geometry + precomputed bbox ---
                "geom_wkb": to_wkb(line),
                "minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy,
            })

df = pd.DataFrame(rows)
df.to_parquet("reaches.parquet", index=False)
print(f"wrote reaches.parquet: {len(df)} reaches, "
      f"states={sorted(df.state.unique())}, huc2={sorted(df.huc2.unique())}")
