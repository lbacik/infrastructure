#!/usr/bin/env bash

#DIRNAME=`dirname "$0"`
#source ${DIRNAME}/../$1

source $1

IMAGE=kylemanna/openvpn:local

docker run --rm -v $OVPN_DATA:/etc/openvpn \
    ${IMAGE} ovpn_genconfig -u udp://${DOMAIN}
docker run -v $OVPN_DATA:/etc/openvpn --rm -it \
    ${IMAGE} ovpn_initpki
docker run -v $OVPN_DATA:/etc/openvpn --rm -it \
    ${IMAGE} easyrsa build-client-full vpnclient nopass
docker run -v $OVPN_DATA:/etc/openvpn --rm \
    ${IMAGE} ovpn_getclient vpnclient > config.ovpn

