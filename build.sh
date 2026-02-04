#!/usr/bin/env bash
set -euo pipefail


if [[ -d "./DEBIAN" ]]; then
  PKG_DIR="."
else
  PKG_DIR="${PKG_DIR:-zks-bootstrap_0.1.0}"
fi

OUT_DEB="${OUT_DEB:-../zks-bootstrap_0.1.0.deb}"


[[ -d "$PKG_DIR/DEBIAN" ]] || { echo "ERROR: $PKG_DIR/DEBIAN not found"; exit 1; }
[[ -f "$PKG_DIR/DEBIAN/control" ]] || { echo "ERROR: missing DEBIAN/control"; exit 1; }
[[ -f "$PKG_DIR/usr/sbin/zks-bootstrap" ]] || { echo "ERROR: missing usr/sbin/zks-bootstrap"; exit 1; }


chmod 0755 "$PKG_DIR/DEBIAN/postinst"
chmod 0755 "$PKG_DIR/DEBIAN/prerm"
chmod 0644 "$PKG_DIR/DEBIAN/control"
chmod 0644 "$PKG_DIR/DEBIAN/conffiles"

chmod 0755 "$PKG_DIR/usr/sbin/zks-bootstrap"

if [[ -d "$PKG_DIR/etc/zks-bootstrap" ]]; then
  chmod 0700 "$PKG_DIR/etc/zks-bootstrap" || true
fi
if [[ -f "$PKG_DIR/etc/zks-bootstrap/config.env" ]]; then
  chmod 0600 "$PKG_DIR/etc/zks-bootstrap/config.env" || true
fi

#bash -n "$PKG_DIR/usr/sbin/zks-bootstrap"

# Build
dpkg-deb --build "$PKG_DIR" "$OUT_DEB"
echo "Built: $OUT_DEB"

echo "Inspect:"
echo "  dpkg-deb -I $OUT_DEB"
echo "  dpkg-deb -c $OUT_DEB"

