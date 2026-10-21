"""Non-destructive institution selection and review flags for public OSM data."""

from collections import Counter
import hashlib
import json
import math
import unicodedata

import geopandas as gpd
import pandas as pd
from pyproj import CRS, Geod
from shapely.geometry import Point


def audit_inventory(collection, boundary, *, analysis_crs,
                    proximity_distance_m=30, same_name_distance_m=250, distance_method="projected"):
    """Select points covered by a polygon, retaining all records and review evidence.

    Input GeoJSON follows longitude/latitude WGS84 conventions. Boundary edges
    are included, polygon holes excluded. Duplicate candidates are heuristics,
    never instructions to merge. Source-row IDs are stable for a fixed source
    snapshot; valid OSM IDs remain stable across snapshots.
    """
    if boundary.crs is None:
        raise ValueError("Boundary CRS must be known")
    metric_crs = CRS.from_user_input(analysis_crs)
    if not metric_crs.is_projected or any(a.unit_name != "metre" for a in metric_crs.axis_info):
        raise ValueError("Analysis CRS must be projected with metre units")
    if any(not math.isfinite(d) or d < 0 for d in [proximity_distance_m, same_name_distance_m]):
        raise ValueError("Review distances must be finite and nonnegative")
    if (boundary.empty or boundary.geometry.isna().any()
            or boundary.geometry.is_empty.any() or not boundary.geometry.is_valid.all()
            or not boundary.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all()):
        raise ValueError("Boundary must contain valid nonempty polygons")
    if collection.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection")
    polygon = boundary.to_crs(4326).geometry.union_all()
    snapshot = hashlib.sha256(json.dumps(collection, sort_keys=True).encode()).hexdigest()[:16]
    selected, log = [], []
    for index, feature in enumerate(collection["features"]):
        props = feature.get("properties") or {}
        source_id = feature.get("id")
        osm_type, osm_id = props.get("osm_type"), props.get("osm_id")
        identity_valid = osm_type in ("node", "way", "relation") and str(osm_id).isdigit()
        canonical = f"{osm_type}/{osm_id}" if identity_valid else None
        identity_issue = not identity_valid or source_id != canonical
        record_id = f"snapshot:{snapshot}:{index}"
        institution_id = f"osm:{canonical}" if identity_valid else record_id
        entry = {"source_record_id": record_id, "source_index": index,
                 "source_feature_id": source_id, "institution_id": institution_id}
        geom = feature.get("geometry") or {}
        xy = geom.get("coordinates")
        if geom.get("type") != "Point":
            log.append(dict(entry, selection_status="unsupported_geometry"))
            continue
        if (not isinstance(xy, (list, tuple)) or len(xy) < 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float))
                       or not math.isfinite(v) for v in xy[:2])
                or not (-180 <= xy[0] <= 180 and -90 <= xy[1] <= 90)):
            log.append(dict(entry, selection_status="invalid_coordinates"))
            continue
        point = Point(xy[:2])
        if not polygon.covers(point):
            log.append(dict(entry, selection_status="outside_boundary"))
            continue
        log.append(dict(entry, selection_status="selected"))
        raw_name = props.get("name")
        name = str(raw_name).strip() if raw_name is not None else ""
        categories = props.get("categories") or []
        if not isinstance(categories, list):
            categories = [str(categories)]
        selected.append(dict(
            entry, osm_type=osm_type, osm_id=str(osm_id) if osm_id is not None else None,
            name=name, source_name=raw_name,
            normalized_name=" ".join(unicodedata.normalize("NFKC", name).casefold().split()),
            categories=";".join(str(c) for c in categories),
            longitude=xy[0], latitude=xy[1], missing_name=not bool(name),
            identity_issue=identity_issue, on_boundary=polygon.boundary.covers(point),
            location_representation="bounding_box_center" if osm_type in ("way", "relation") else "osm_point",
            coordinate_review_status="not_independently_verified",
            tags_json=json.dumps(props.get("tags") or {}, ensure_ascii=False, sort_keys=True),
            geometry=point))
    columns = ["source_record_id", "source_index", "source_feature_id", "institution_id",
               "osm_type", "osm_id", "name", "source_name", "normalized_name", "categories",
               "longitude", "latitude", "missing_name", "identity_issue", "on_boundary",
               "location_representation", "coordinate_review_status", "tags_json", "geometry"]
    institutions = gpd.GeoDataFrame(selected, columns=columns, geometry="geometry", crs=4326)
    id_counts = Counter(institutions.institution_id)
    institutions["repeated_identity"] = institutions.institution_id.map(lambda v: id_counts[v] > 1).astype(bool)
    if distance_method not in ("projected", "geodesic"):
        raise ValueError("Distance method must be projected or geodesic")
    projected = institutions.to_crs(metric_crs) if distance_method == "projected" else None
    metric_geometries = list(projected.geometry) if projected is not None else None
    geod = Geod(ellps="WGS84")
    records = institutions.to_dict("records")
    pairs = []
    for i, a in enumerate(records):
        for j in range(i + 1, len(records)):
            b = records[j]
            distance = (geod.inv(a["longitude"], a["latitude"], b["longitude"], b["latitude"])[2]
                        if distance_method == "geodesic" else metric_geometries[i].distance(metric_geometries[j]))
            reasons = []
            if a["institution_id"] == b["institution_id"]:
                reasons.append("repeated_identity")
            if distance <= proximity_distance_m:
                reasons.append("nearby_locations")
            if a["normalized_name"] and a["normalized_name"] == b["normalized_name"] and distance <= same_name_distance_m:
                reasons.append("same_name_nearby")
            if reasons:
                pairs.append({"record_a": a["source_record_id"], "record_b": b["source_record_id"],
                              "institution_a": a["institution_id"], "institution_b": b["institution_id"],
                              "name_a": a["name"], "name_b": b["name"], "distance_m": distance,
                              "reasons": ";".join(reasons), "review_status": "unreviewed", "review_notes": ""})
    pair_columns = ["record_a", "record_b", "institution_a", "institution_b", "name_a", "name_b",
                    "distance_m", "reasons", "review_status", "review_notes"]
    candidates = pd.DataFrame(pairs, columns=pair_columns)
    counts = Counter([r[k] for r in pairs for k in ("record_a", "record_b")])
    institutions["candidate_pair_count"] = institutions.source_record_id.map(lambda v: counts[v]).astype(int)
    selection = pd.DataFrame(log, columns=["source_record_id", "source_index", "source_feature_id", "institution_id", "selection_status"])
    return {"institutions": institutions, "selection": selection, "duplicate_candidates": candidates}
