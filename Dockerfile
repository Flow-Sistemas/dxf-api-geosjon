FROM osgeo/gdal:ubuntu-small-3.8.5

# Instala Python e bindings do GDAL para Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-gdal \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependências Python da aplicação
RUN pip3 install --no-cache-dir --upgrade pip \
 && pip3 install --no-cache-dir fastapi uvicorn[standard] pydantic

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8000
ENV PORT=8000
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
