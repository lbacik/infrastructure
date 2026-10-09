ARG LITELLM_VERSION
FROM ghcr.io/berriai/litellm:${LITELLM_VERSION}

# Baked in rather than bind-mounted so the project also deploys through remote
# (ssh://) Docker contexts, where bind-mount sources resolve on the remote host.
COPY ./config.yaml /app/config.yaml
