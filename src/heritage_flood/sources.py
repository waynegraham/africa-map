"""Inspect public catalogue footprints and OSM outlines without asserting ground truth."""

from datetime import datetime
import math

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import Polygon, shape


def osm_way_outline(payload, way_id):
    """Return an unmodified closed OSM way polygon, rejecting incomplete chains."""
    ways = [e for e in payload["elements"] if e["type"] == "way" and e["id"] == way_id]
    if len(ways) != 1:
        raise ValueError("Expected exactly one requested OSM way")
    refs = ways[0].get("nodes", [])
    nodes = {e["id"]: e for e in payload["elements"] if e["type"] == "node"}
    if len(refs) < 4 or refs[0] != refs[-1] or any(n not in nodes for n in refs):
        raise ValueError("Outline requires a complete closed node chain")
    xy = [(nodes[n]["lon"], nodes[n]["lat"]) for n in refs]
    if any(not math.isfinite(x) or not math.isfinite(y)
           or not (-180 <= x <= 180 and -90 <= y <= 90) for x, y in xy):
        raise ValueError("Invalid OSM coordinates")
    polygon = Polygon(xy)
    if polygon.is_empty or not polygon.is_valid or polygon.area == 0:
        raise ValueError("OSM outline is not a valid polygon; no automatic repair applied")
    return polygon


def scene_manifest(items, boundary, institutions, *, analysis_crs):
    """Return scene footprints and metadata; footprint coverage is not pixel usability.

    Catalogue IDs and processing metadata are retained. No Earth Engine asset
    identity, image downloadability, cloud-free pixels, or flood evidence is
    inferred from catalogue presence.
    """
    metric = CRS.from_user_input(analysis_crs)
    if not metric.is_projected or any(a.unit_name != "metre" for a in metric.axis_info):
        raise ValueError("Analysis CRS must use projected metre units")
    for frame in (boundary, institutions):
        if frame.crs is None:
            raise ValueError("Input CRS must be known")
        if frame.geometry.isna().any() or frame.is_empty.any() or not frame.is_valid.all():
            raise ValueError("Input geometry must be valid and nonempty")
    if boundary.empty or not boundary.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ValueError("Boundary must contain polygons")
    if not institutions.geom_type.eq("Point").all():
        raise ValueError("Institution geometry must be points")
    keys = [(x["collection"], x["id"]) for x in items]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate catalogue IDs: review pagination and processing versions")
    municipality = boundary.to_crs(metric).geometry.union_all()
    points = institutions.to_crs(4326)
    rows = []
    for item in items:
        props = item["properties"]
        acquired = props.get("datetime") or props.get("start_datetime")
        if not acquired or datetime.fromisoformat(acquired.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("Acquisition timestamp must include timezone")
        geom = shape(item["geometry"])
        if geom.is_empty or not geom.is_valid or geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError("Scene footprint must be a valid polygon")
        projected = gpd.GeoSeries([geom], crs=4326).to_crs(metric).iloc[0]
        ids = [str(row.institution_id) for row in points.itertuples() if geom.covers(row.geometry)]
        rows.append({
            "catalogue_collection": item["collection"], "catalogue_id": item["id"],
            "acquired_at_utc": acquired, "platform": props.get("platform"),
            "product_type": props.get("product:type"), "relative_orbit": props.get("sat:relative_orbit"),
            "orbit_state": props.get("sat:orbit_state"), "sar_mode": props.get("sar:instrument_mode"),
            "polarizations": ";".join(props.get("sar:polarizations", [])),
            "grid_code": props.get("grid:code"), "cloud_cover_scene_pct": props.get("eo:cloud_cover"),
            "sar_pixel_spacing_range_m": props.get("sar:pixel_spacing_range"),
            "sar_pixel_spacing_azimuth_m": props.get("sar:pixel_spacing_azimuth"),
            "processing_version": props.get("processing:version"),
            "processing_datetime": props.get("processing:datetime"),
            "municipality_footprint_fraction": projected.intersection(municipality).area / municipality.area,
            "covered_institution_ids": ";".join(ids), "covered_institution_count": len(ids),
            "pixel_usability": "not_evaluated", "earth_engine_asset_id": None,
            "geometry": geom,
        })
    columns = ["catalogue_collection", "catalogue_id", "acquired_at_utc", "platform", "product_type",
               "relative_orbit", "orbit_state", "sar_mode", "polarizations", "grid_code",
               "cloud_cover_scene_pct", "sar_pixel_spacing_range_m", "sar_pixel_spacing_azimuth_m",
               "processing_version", "processing_datetime", "municipality_footprint_fraction",
               "covered_institution_ids", "covered_institution_count", "pixel_usability",
               "earth_engine_asset_id", "geometry"]
    return gpd.GeoDataFrame(rows, columns=columns, geometry="geometry", crs=4326)


def pixel_quality_summary(record):
    """Interpret mask counts without treating missing or cloudy samples as dry.

    Earth Engine sum reducers weight region-edge pixels, so counts may be
    fractional. Fractions describe the specified sampling grid/context only.
    """
    sensor, metrics = record["sensor"], record["metrics"]
    if sensor not in ("S1", "S2"):
        raise ValueError("Expected S1 or S2 quality metrics")
    result = {"valid_fraction": None, "conservative_clear_fraction": None,
              "quality_status": "missing_metrics"}
    total = metrics.get("total")
    if total is None:
        return result
    if not math.isfinite(total) or total < 0:
        raise ValueError("Invalid total sampling weight")
    if total == 0:
        return dict(result, quality_status="no_grid_samples")
    valid = metrics.get("valid" if sensor == "S1" else "spectral_valid")
    clear = metrics.get("conservative_clear") if sensor == "S2" else None
    for value in [valid, clear, metrics.get("scl_valid")]:
        if value is not None and (not math.isfinite(value) or value < 0 or value > total + 1e-6):
            raise ValueError("Sampling weights must lie between zero and total")
    if valid is None:
        return result
    result["valid_fraction"] = min(1.0, valid / total)
    if sensor == "S1":
        result["quality_status"] = "valid_data_requires_sar_review" if valid else "no_valid_samples"
    elif clear is not None:
        if clear > valid + 1e-6:
            raise ValueError("Clear sampling weight exceeds spectral-valid weight")
        result["conservative_clear_fraction"] = min(1.0, clear / total)
        result["quality_status"] = "clear_candidate_requires_visual_review" if clear else "no_conservative_clear_samples"
    return result
