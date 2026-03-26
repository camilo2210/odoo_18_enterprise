FROM odoo:19.0  # O la versión que utilices
USER root
RUN pip3 install --no-cache-dir paramiko
USER odoo
