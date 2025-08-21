# DXF → GeoJSON API (GDAL/OGR) — Build estável com imagem OSGeo

Este pacote usa a imagem base **osgeo/gdal:ubuntu-small-3.8.5** para evitar erros de binding do GDAL (`_gdal`, `osgeo`).

## Build & Run
```bash
docker build -t dxf2geojson .
docker run --rm -p 8000:8000 dxf2geojson
curl http://localhost:8000/health
```

Se `status` vier `"ok"`, os bindings estão ativos. Se vier `"degraded"`, a imagem não tem GDAL com Python — verifique o Dockerfile.

## Observação
O `app.py` agora faz **lazy import** do GDAL/OGR, evitando crash no boot caso o ambiente esteja sem os bindings; o `/convert` falhará com 500 informando o motivo.
