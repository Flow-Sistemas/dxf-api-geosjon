import base64
import json
import os
import tempfile
from typing import Optional, Literal, Dict, Any, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, constr

# GDAL / OGR
from osgeo import ogr, osr, gdal

app = FastAPI(title="DXF → GeoJSON API", version="1.0.0", docs_url="/docs", redoc_url="/redoc")

# Tornar erros do GDAL mais verbosos em logs
gdal.UseExceptions()


class ConvertRequest(BaseModel):
    dxf_base64: constr(strip_whitespace=True, min_length=1) = Field(..., description="Conteúdo DXF em base64")
    source_crs: Optional[str] = Field(None, description="CRS de origem (ex: 'EPSG:31982'). Se omitido, mantém coordenadas originais")
    target_crs: Optional[str] = Field("EPSG:4326", description="CRS de saída (padrão: WGS84)")
    keep_original_coords: bool = Field(False, description="Se True, ignora reprojeção e mantém as coordenadas do DXF")
    include_ogr_fields: bool = Field(True, description="Se True, inclui todos os campos lidos pelo OGR nas propriedades")


class HealthResponse(BaseModel):
    status: Literal["ok"]
    gdal_version: str
    ogr_drivers: List[str]


def _build_coord_transform(source_epsg: Optional[str], target_epsg: Optional[str]):
    """
    Cria um transformador de coordenadas OGR/OSR.
    Retorna (transform, src_srs, dst_srs), ou (None, None, None) se não houver reprojeção.
    """
    if not source_epsg or not target_epsg or source_epsg == target_epsg:
        return None, None, None

    src_srs = osr.SpatialReference()
    if src_srs.SetFromUserInput(source_epsg) != 0:
        raise ValueError(f"Não foi possível interpretar source_crs: {source_epsg}")

    dst_srs = osr.SpatialReference()
    if dst_srs.SetFromUserInput(target_epsg) != 0:
        raise ValueError(f"Não foi possível interpretar target_crs: {target_epsg}")

    transform = osr.CoordinateTransformation(src_srs, dst_srs)
    return transform, src_srs, dst_srs


def _feature_properties(feat: ogr.Feature, include_ogr_fields: bool) -> Dict[str, Any]:
    props: Dict[str, Any] = {}

    if include_ogr_fields:
        defn = feat.GetDefnRef()
        for i in range(defn.GetFieldCount()):
            fdefn = defn.GetFieldDefn(i)
            name = fdefn.GetName()
            val = feat.GetField(i)
            if isinstance(val, bytes):
                val = val.decode(errors="ignore")
            props[name] = val

    layer_name = feat.GetDefnRef().GetName() if feat.GetDefnRef() else None
    if layer_name and "layer" not in props:
        props["layer"] = layer_name

    for key in ("Text", "MTEXT", "TEXT", "MText"):
        if feat.GetFieldIndex(key) != -1 and key not in props:
            props[key] = feat.GetField(key)

    return props


def _export_geom(geom: ogr.Geometry, transform: Optional[osr.CoordinateTransformation]) -> Optional[Dict[str, Any]]:
    if geom is None:
        return None
    geom_clone = geom.Clone()

    if transform is not None:
        try:
            geom_clone.Transform(transform)
        except Exception:
            return None

    try:
        geom_json = json.loads(geom_clone.ExportToJson())
        return geom_json
    except Exception:
        return None


def _collect_layers_as_features(ds: ogr.DataSource,
                                transform: Optional[osr.CoordinateTransformation],
                                include_ogr_fields: bool) -> List[Dict[str, Any]]:
    features: List[Dict[str, Any]] = []
    for i in range(ds.GetLayerCount()):
        layer = ds.GetLayerByIndex(i)
        if layer is None:
            continue

        layer.ResetReading()
        for feat in layer:
            try:
                geom = feat.GetGeometryRef()
                gj = _export_geom(geom, transform)
                if gj is None:
                    continue

                props = _feature_properties(feat, include_ogr_fields)
                features.append({
                    "type": "Feature",
                    "geometry": gj,
                    "properties": props
                })
            except Exception:
                continue
    return features


def _compute_bbox(features: List[Dict[str, Any]]) -> Optional[List[float]]:
    minx = miny = float("inf")
    maxx = maxy = float("-inf")

    def scan_coords(coords):
        nonlocal minx, miny, maxx, maxy
        if isinstance(coords[0], (float, int)):
            x, y = coords[:2]
            minx = min(minx, x); miny = min(miny, y)
            maxx = max(maxx, x); maxy = max(maxy, y)
        else:
            for c in coords:
                scan_coords(c)

    for f in features:
        geom = f.get("geometry")
        if not geom:
            continue
        coords = geom.get("coordinates")
        if coords is None:
            continue
        try:
            scan_coords(coords)
        except Exception:
            continue

    if minx is float("inf"):
        return None
    return [minx, miny, maxx, maxy]


@app.get("/health", response_model=HealthResponse)
def health():
    drivers = []
    for i in range(ogr.GetDriverCount()):
        drv = ogr.GetDriver(i)
        if drv:
            drivers.append(drv.GetName())
    return HealthResponse(status="ok", gdal_version=gdal.VersionInfo(), ogr_drivers=drivers)


@app.post("/convert")
def convert(req: ConvertRequest):
    try:
        dxf_bytes = base64.b64decode(req.dxf_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="dxf_base64 inválido")

    if len(dxf_bytes) == 0:
        raise HTTPException(status_code=400, detail="DXF vazio")

    MAX_BYTES = 200 * 1024 * 1024  # 200 MB
    if len(dxf_bytes) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Arquivo acima do limite ({MAX_BYTES} bytes)")

    with tempfile.TemporaryDirectory() as tmpdir:
        dxf_path = os.path.join(tmpdir, "input.dxf")
        with open(dxf_path, "wb") as f:
            f.write(dxf_bytes)

        ds = ogr.Open(dxf_path)
        if ds is None:
            raise HTTPException(status_code=422, detail="Falha ao abrir DXF com OGR. Verifique se o arquivo é DXF válido.")

        transform = None
        if not req.keep_original_coords and req.source_crs and req.target_crs:
            try:
                transform, _, _ = _build_coord_transform(req.source_crs, req.target_crs)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        features = _collect_layers_as_features(ds, transform, req.include_ogr_fields)

        fc: Dict[str, Any] = {
            "type": "FeatureCollection",
            "features": features,
        }

        bbox = _compute_bbox(features)
        if bbox:
            fc["bbox"] = bbox

        if not req.keep_original_coords and req.target_crs:
            fc["crs"] = {"type": "name", "properties": {"name": req.target_crs}}

        return fc
