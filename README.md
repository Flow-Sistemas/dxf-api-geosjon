# DXF → GeoJSON API (FastAPI + GDAL/OGR)

API que recebe um arquivo **DXF** em **base64** via `POST /convert` e retorna um **GeoJSON FeatureCollection** com todas as entidades possíveis (LINE, LWPOLYLINE, POLYLINE, CIRCLE, ARC, SPLINE, ELLIPSE, POINT, TEXT/MTEXT etc.).

- Driver: **GDAL/OGR** (robusto para DXF complexos)
- Reprojeção opcional para **EPSG:4326 (WGS84)** com `source_crs` → `target_crs`
- Dockerfile pronto para **Railway**

## Endpoints

- `GET /health` — retorna versão do GDAL e drivers OGR instalados
- `POST /convert` — corpo JSON:
  ```json
  {
    "dxf_base64": "<COLE_AQUI_SEU_DXF_EM_BASE64>",
    "source_crs": "EPSG:31982",
    "target_crs": "EPSG:4326",
    "keep_original_coords": false,
    "include_ogr_fields": true
  }
  ```

## Rodando com Docker (recomendado)
```bash
docker build -t dxf2geojson .
docker run --rm -p 8000:8000 dxf2geojson
# Teste
curl http://localhost:8000/health
```

## Exemplo de uso
```bash
# monte o corpo de requisição em examples/request.json e envie:
curl -X POST http://localhost:8000/convert \
  -H "Content-Type: application/json" \
  -d @examples/request.json
```

## Observações
- Para DXFs em coordenadas planas (UTM/SIRGAS etc.), informe `source_crs` (ex.: `EPSG:31982`, `EPSG:31983`, `EPSG:4674`) para obter saída em WGS84 (padrão).
- Se quiser manter as coordenadas **exatas** do arquivo, use `"keep_original_coords": true`.
- `include_ogr_fields` inclui todos os atributos que o OGR conseguir ler (útil para depuração de camadas e estilos CAD).
- Limite padrão de upload: 200 MB (ajuste em `app.py`).

## Deploy na Railway
1. Faça push desses arquivos para um repositório no GitHub.
2. Na Railway, crie um projeto a partir do **repositório** (o Dockerfile será detectado).
3. Não precisa definir Start Command (o Dockerfile já utiliza `uvicorn`).
4. Após o deploy, teste `GET /health` e depois `POST /convert`.

## Licença
MIT (ajuste conforme sua necessidade).
