#!/bin/sh
# Renders an authoritative zone for every entry of ZONES (space separated):
# apex and default.<zone> point at HOST_IP, every other name is a wildcard
# CNAME to default.<zone>. DOMAIN is this server's own name (the NS target).
set -eu

conf=/etc/dnsmasq.d/zones.conf

if [ -n "${ZONES:-}" ]; then
  {
    echo "auth-server=${DOMAIN:?},eth0"
    echo "auth-soa=${SOA_SERIAL:?},hostmaster.luka.sh,3600,600,604800"
    echo "auth-ttl=3600"
    for zone in $ZONES; do
      echo "auth-zone=$zone"
      echo "host-record=$zone,${HOST_IP:?}"
      echo "host-record=default.$zone,$HOST_IP"
      echo "cname=*.$zone,default.$zone"
    done
  } > "$conf"
else
  rm -f "$conf"
fi

exec /usr/sbin/dnsmasq --keep-in-foreground "$@"
