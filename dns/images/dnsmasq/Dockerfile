FROM 4km3/dnsmasq

ARG DNSMASQ_CONF=dnsmasq.conf

COPY ./conf/${DNSMASQ_CONF} /etc/dnsmasq.d/dev-env.conf
COPY --chmod=755 ./entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# COPY ./conf/hosts /usr/local/etc/dnsmasq/hosts
# COPY ./conf/resolv.conf /usr/local/etc/dnsmasq/resolv.conf
# COPY ./conf/etc-resolv.conf /etc/resolv.conf
