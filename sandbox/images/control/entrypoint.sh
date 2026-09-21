#!/bin/sh
set -e
# alias comodo: `docker exec sbx-control odoolab ...`
if [ ! -e /usr/local/bin/odoolab ]; then
  printf '#!/bin/sh\nexec python -m odoolab.cli "$@"\n' > /usr/local/bin/odoolab
  chmod +x /usr/local/bin/odoolab
fi
exec "$@"
