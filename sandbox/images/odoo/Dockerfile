ARG ODOO_VERSION=16.0
FROM odoo:${ODOO_VERSION}
ARG ODOO_VERSION
USER root
# Sin apt a proposito: los indices de las bases Debian viejas (bullseye para
# odoo:16.0) se desincronizan del mirror y rompen el build con 404.
# Lo unico que el runtime necesita es openupgradelib, que usan los scripts de
# OpenUpgrade. git y odoo-module-migrator viven en la imagen de control.
RUN pip3 install --no-cache-dir --break-system-packages openupgradelib \
 || pip3 install --no-cache-dir openupgradelib
# /mnt/extra-addons = modulos custom | /opt/oca = OpenUpgrade | /opt/tool = herramienta propia
RUN mkdir -p /mnt/extra-addons /opt/oca /opt/tool && chown -R odoo:odoo /mnt/extra-addons
ENV ODOO_VERSION=${ODOO_VERSION}
USER odoo
