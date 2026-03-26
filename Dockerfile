FROM odoo:18.0  # O la versión que utilices
USER root
RUN pip3 install --no-cache-dir paramiko
USER odoo
