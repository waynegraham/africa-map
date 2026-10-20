"""Provisional point screening against mapped floodplain polygons."""

import math

from pyproj import CRS


def screen_floodplain(institutions, floodplain, *, analysis_crs, buffer_distances_m=()):
    """Retain point records and report mapped overlap, never infer absent hazard.

    Buffers are sensitivity distances around unverified points, not flood
    probabilities or building footprints. No coverage mask is available here.
    Invalid source polygons must be explicitly reviewed/prepared by the caller.
    """
    metric = CRS.from_user_input(analysis_crs)
    if not metric.is_projected or any(a.unit_name != "metre" for a in metric.axis_info):
        raise ValueError("Analysis CRS must use projected metre units")
    for frame in (institutions, floodplain):
        if frame.crs is None:
            raise ValueError("Every input must have a verified CRS")
        if frame.geometry.isna().any() or frame.geometry.is_empty.any() or not frame.geometry.is_valid.all():
            raise ValueError("Inputs must contain valid nonempty geometries")
    if floodplain.empty or not floodplain.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ValueError("Floodplain must contain polygons")
    if not institutions.geom_type.eq("Point").all():
        raise ValueError("Institutions must be points")
    radii = list(buffer_distances_m)
    if any(isinstance(r, bool) or not isinstance(r, (int, float))
           or not math.isfinite(r) or r <= 0 or int(r) != r for r in radii):
        raise ValueError("Sensitivity radii must be positive integer metres")
    projected_points = institutions.to_crs(metric)
    mapped = floodplain.to_crs(metric).geometry.union_all()
    result = institutions.copy()
    result["point_intersects"] = projected_points.intersects(mapped).to_numpy()
    result["distance_to_mapped_floodplain_m"] = projected_points.distance(mapped).to_numpy()
    result["screening_status"] = ["intersects_mapped_floodplain" if x else
                                  "no_mapped_intersection_coverage_unknown" for x in result.point_intersects]
    result["coverage_status"] = "completeness_not_established"
    for radius in sorted(set(radii)):
        result[f"buffer_{int(radius)}m_intersects"] = result.distance_to_mapped_floodplain_m <= radius
    return result
