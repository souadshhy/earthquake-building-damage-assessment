import numpy as np
from affine import Affine
from shapely import wkt
from shapely.geometry import Polygon, mapping
from rasterio.warp import transform_geom


def annotation_transform(annotation):
    """Fit per-image affine; validate on buildings not used in fitting."""
    xy = {f["properties"]["uid"]: f for f in annotation["features"]["xy"]}
    geo = {f["properties"]["uid"]: f for f in annotation["features"]["lng_lat"]}
    if xy.keys() != geo.keys() or len(xy) < 4:
        raise ValueError("At least four matching pixel/geographic buildings are required")
    X, Y, ids = [], [], []
    for uid in sorted(xy):
        a = list(wkt.loads(xy[uid]["wkt"]).exterior.coords)[:-1]
        b = list(wkt.loads(geo[uid]["wkt"]).exterior.coords)[:-1]
        if len(a) != len(b):
            raise ValueError("Pixel/geographic vertex mismatch")
        X.extend([[x, y, 1] for x, y in a])
        Y.extend(b)
        ids.extend([uid] * len(a))
    X, Y = np.asarray(X), np.asarray(Y)
    fit_ids = sorted(xy)[:max(3, int(len(xy) * 0.7))]
    train = np.isin(ids, fit_ids)
    if np.linalg.matrix_rank(X[train]) != 3:
        raise ValueError("Degenerate geographic control points")
    coefficients = np.linalg.lstsq(X[train], Y[train], rcond=None)[0]
    errors = (X[~train] @ coefficients - Y[~train]) * [
        111320 * np.cos(np.deg2rad(Y[:, 1].mean())), 111320]
    maximum = float(np.linalg.norm(errors, axis=1).max())
    if not np.isfinite(maximum) or maximum > 1:
        raise ValueError(f"Internal affine consistency failed ({maximum:.2f} m)")
    transform = Affine(coefficients[0, 0], coefficients[1, 0], coefficients[2, 0],
                       coefficients[0, 1], coefficients[1, 1], coefficients[2, 1])
    return list(transform)[:6], maximum


def pixel_geometry_to_geo(geometry, transform, crs):
    affine = Affine(*transform)
    def ring(points):
        return [affine * tuple(point) for point in points]
    if geometry["type"] != "Polygon":
        raise ValueError("Expected polygon")
    projected = {"type": "Polygon", "coordinates": [ring(r) for r in geometry["coordinates"]]}
    return transform_geom(crs, "EPSG:4326", projected)


def tile_footprint(transform, width, height):
    affine = Affine(*transform)
    return Polygon([affine * p for p in [(0, 0), (width, 0), (width, height), (0, height)]])
