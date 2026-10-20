"""Build the local-only eThekwini research map from registered derived inputs."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling, transform_bounds
from PIL import Image


def build_research_map(root, destination=None):
    """Build an HTTP-served local bundle; never write into published docs/."""
    root = Path(root).resolve()
    destination = Path(destination or root / "outputs/research_map").resolve()
    published = root / "docs"
    if destination == published or published in destination.parents:
        raise ValueError("Research map must remain outside published docs/")
    data = root / "data/processed/ethekwini"
    inputs = [data / "floodplain_screening.geojson", data / "floodplain_screening.gpkg",
              data / "municipal_boundary.gpkg"]
    institutions = json.loads(inputs[0].read_text())
    boundary = gpd.read_file(inputs[2], layer="municipal_boundary").to_crs(4326)
    flood = gpd.read_file(inputs[1], layer="mapped_floodplain").to_crs(32736)
    # Display-only simplification; analytical source geometry is unchanged.
    flood.geometry = flood.geometry.simplify(2, preserve_topology=True)
    fields = [c for c in ["OBJECTID", "RIVER_NAME", "CAPT_DATE", "geometry"] if c in flood.columns]
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    vendor = root / "data/raw/web_vendor"
    for name in ["leaflet.js", "leaflet.css", "LICENSE"]:
        if not (vendor / name).is_file():
            raise FileNotFoundError(f"Missing local Leaflet vendor file: {vendor / name}")
    shutil.copytree(vendor, destination / "vendor", dirs_exist_ok=True)
    web = Path(__file__).parent / "web"
    for name in ["index.html", "map.css", "map.js"]:
        shutil.copyfile(web / name, destination / name)
    profiles = {}
    decisions = root / "metadata/site_review_decisions.csv"
    if decisions.exists():
        inputs.append(decisions)
        for row in json.loads(pd.read_csv(decisions).to_json(orient="records")):
            profiles.setdefault(row["institution_id"], {})["identity_review"] = row
    outlines_path = data / "flagged_site_review.gpkg"
    outlines = {"type": "FeatureCollection", "features": []}
    if outlines_path.exists():
        inputs.append(outlines_path)
        frame = gpd.read_file(outlines_path, layer="osm_outlines").to_crs(4326)
        outlines = json.loads(frame[["institution_id", "geometry"]].to_json())
    for filename, key in [("earth_engine_site_quality.csv", "quality"),
                          ("flagged_site_geometry_review.csv", "geometry_review")]:
        path = data / filename
        if path.exists():
            inputs.append(path)
            for row in json.loads(pd.read_csv(path).to_json(orient="records")):
                profiles.setdefault(row["institution_id"], {}).setdefault(key, []).append(row)
    for feature in institutions["features"]:
        props = feature["properties"]
        site = props.get("institution_id", "").split("/")[-1]
        if not site.isdigit():
            continue
        images = []
        for prefix, title in [("visual_review", "Optical and SAR comparison"), ("sar_change", "Exploratory SAR changes")]:
            path = root / "outputs/figures" / f"{prefix}_{site}.png"
            if path.exists():
                shutil.copyfile(path, assets / path.name)
                inputs.append(path)
                images.append({"title": title, "path": "assets/" + path.name})
        profiles.setdefault(props["institution_id"], {})["images"] = images
    overlays = []
    for site in ["368501740", "1199992499"]:
        path = data / f"sar_change_{site}.tif"
        if not path.exists():
            continue
        inputs.append(path)
        with rasterio.open(path) as source:
            values = source.read(5).astype(float)
            values[source.read(14) != 1] = np.nan
            affine, width, height = calculate_default_transform(source.crs, "EPSG:3857", source.width, source.height, *source.bounds)
            warped = np.full((height, width), np.nan, dtype="float32")
            reproject(values, warped, src_transform=source.transform, src_crs=source.crs,
                      src_nodata=np.nan, dst_transform=affine, dst_crs="EPSG:3857",
                      dst_nodata=np.nan, resampling=Resampling.nearest)
            import matplotlib
            colors = matplotlib.colormaps["RdBu"](np.clip((np.nan_to_num(warped) + 6) / 12, 0, 1), bytes=True)
            colors[:, :, 3] = np.where(np.isfinite(warped), 210, 0)
            filename = f"sar_vv_change_{site}.png"
            Image.fromarray(colors).save(assets / filename)
            west, south, east, north = transform_bounds("EPSG:3857", "EPSG:4326",
                affine.c, affine.f + height * affine.e, affine.c + width * affine.a, affine.f)
            overlays.append({"site": site, "path": "assets/" + filename,
                             "bounds": [[south, west], [north, east]]})
    payload = {"institutions": institutions, "boundary": json.loads(boundary.to_json()),
               "floodplain": json.loads(flood[fields].to_crs(4326).to_json()),
               "profiles": profiles, "reviewed_outlines": outlines, "sar_overlays": overlays,
               "built_at_utc": datetime.now(timezone.utc).isoformat()}
    (destination / "data.json").write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    manifest = {"purpose": "Local research presentation; no publication or new hazard analysis",
                "inputs_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                "code_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), *(web / n for n in ["index.html", "map.css", "map.js"])]},
                "display": {"floodplain_simplification_m": 2, "sar_vv_range_db": [-6, 6],
                            "sar_resampling": "nearest; warped to Web Mercator for Leaflet image alignment"}}
    (destination / "build_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return destination / "index.html"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(build_research_map(args.root))
