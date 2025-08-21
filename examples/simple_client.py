import base64, json, sys, requests

"""
Uso:
python simple_client.py caminho/para/arquivo.dxf http://localhost:8000/convert EPSG:31982

source_crs é opcional.
"""

path = sys.argv[1]
url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000/convert"
source = sys.argv[3] if len(sys.argv) > 3 else None

with open(path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

payload = {
    "dxf_base64": b64,
    "source_crs": source,
    "target_crs": "EPSG:4326",
    "keep_original_coords": False,
    "include_ogr_fields": True
}

resp = requests.post(url, json=payload, timeout=120)
resp.raise_for_status()
print(json.dumps(resp.json(), ensure_ascii=False))
