ARG ODOO_VERSION=16.0
FROM odoo:${ODOO_VERSION}
ARG ODOO_VERSION
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      git postgresql-client jq curl rsync \
    && rm -rf /var/lib/apt/lists/*
# openupgradelib: lo necesita OpenUpgrade y tambien suele usarse en scripts propios.
RUN pip3 install --no-cache-dir --break-system-packages openupgradelib || \
    pip3 install --no-cache-dir openupgradelib
# addons extra: /mnt/extra-addons (custom), /opt/oca/<ver> (OpenUpgrade), /opt/tool (tu herramienta)
RUN mkdir -p /mnt/extra-addons /opt/oca /opt/tool && chown -R odoo:odoo /mnt/extra-addons /opt/oca
ENV ODOO_VERSION=${ODOO_VERSION}
USER odoo
