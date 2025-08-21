FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# GDAL + bindings Python do Debian (evita compilação via pip)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev python3-gdal proj-bin curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# O módulo 'osgeo' instalado via apt fica em /usr/lib/python3/dist-packages
# Adicionamos esse caminho ao PYTHONPATH para que o Python do container (em /usr/local) encontre o pacote.
ENV PYTHONPATH=/usr/lib/python3/dist-packages:$PYTHONPATH

# Dependências Python da aplicação
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir fastapi uvicorn[standard] pydantic

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8000
ENV PORT=8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
