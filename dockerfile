FROM odoo:19.0

USER root

# Instalar dependencias del sistema necesarias para pgvector y compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar librerías Python
RUN pip3 install --no-cache-dir \
    paramiko \
    pgvector

USER odoo
