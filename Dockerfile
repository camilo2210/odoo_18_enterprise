FROM odoo:18.0

USER root

# Instalar dependencias del sistema (opcional)
RUN apt-get update && apt-get install -y \
    python3-pip \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivo de requerimientos
COPY requirements.txt /tmp/requirements.txt

# Instalar librerías Python adicionales
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Volver al usuario odoo
USER odoo
