FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Use GDAL from Debian repos, including the Python bindings (python3-gdal).
# This avoids compiling GDAL from source via pip (which often fails on slim images).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev python3-gdal curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install only the app deps via pip (no GDAL here).
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir fastapi uvicorn[standard] pydantic

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8000
ENV PORT=8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
