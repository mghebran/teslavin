#!/usr/bin/env bash
# Generates the EC key pair Tesla requires for partner registration.
# Public key must be served at: https://<domain>/.well-known/appspecific/com.tesla.3p.public-key.pem
set -euo pipefail
mkdir -p keys site/.well-known/appspecific
if [ -f keys/private-key.pem ]; then
  echo "keys/private-key.pem already exists; refusing to overwrite." >&2; exit 1
fi
openssl ecparam -name prime256v1 -genkey -noout -out keys/private-key.pem
openssl ec -in keys/private-key.pem -pubout -out keys/public-key.pem
cp keys/public-key.pem site/.well-known/appspecific/com.tesla.3p.public-key.pem
chmod 600 keys/private-key.pem
echo "Private key: keys/private-key.pem  (keep secret, never deploy)"
echo "Public key : site/.well-known/appspecific/com.tesla.3p.public-key.pem  (deploy with the site)"
openssl ec -pubin -in keys/public-key.pem -text -noout 2>/dev/null | grep "ASN1 OID"   # must say prime256v1
