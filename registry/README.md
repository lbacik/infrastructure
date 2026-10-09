# registry

Docker image registry (`registry:2`) plus a browsable web UI
(`joxit/docker-registry-ui`). Deployed like every other project here — see the
root `README.md` for the `docker compose` invocation and the env file layout.

Three shapes, depending on what the host needs:

| files | what you get |
| --- | --- |
| `compose.yaml` | registry reachable only inside the shared docker network (`local`) |
| `+ compose.override.yaml` | plus a fixed `ipv4_address`/alias on that network (`ale`) |
| `+ compose.public.yaml` | plus htpasswd auth and internet exposure through proxy-ssl (`rum`) |

`compose.override.yaml` and `compose.public.yaml` are independent of each
other; nothing stops them being layered together, but no host does that today.

On `rum` the registry stands in for `ghcr.io` as the image store for GitHub
Actions builds of private repositories:

```bash
docker compose \
  --project-directory monorepo/registry \
  -f monorepo/registry/compose.yaml \
  -f monorepo/registry/compose.public.yaml \
  --env-file configurations/rum/registry.env \
  -p registry \
  up -d
```

## The two one-shot containers

`compose.public.yaml` adds `auth` and `proxy-config` alongside the two
long-running services. Both do their work at deploy time, exit 0, and then sit
in `docker ps -a` as `Exited (0)`. That is the finished state, not a failure —
`registry` waits on both via `depends_on: service_completed_successfully`, so
they have already done their job by the time it starts.

Removing the exited containers by hand is safe; the next `up -d` recreates and
re-runs them. What must **not** be removed is the volume each one writes to,
since that is where the actual result lives.

### `auth` — writes the htpasswd file

`registry:2` can only read credentials from a file, and it accepts bcrypt
hashes only. The obvious way to supply one — bind-mounting a file from the
repo — does not work here: bind mount sources resolve on the machine running
the daemon, and these projects are routinely deployed from a workstation
against a remote host, where that path does not exist.

So the file is generated instead. `auth` runs `htpasswd -Bbc` over
`REGISTRY_USER`/`REGISTRY_PASSWORD` from the env file and writes
`/auth/htpasswd` into the `registry-auth` volume, which `registry` mounts
read-only. Rotating the password is therefore just an edit to the env file
followed by a redeploy.

Delete the `registry-auth` volume and the registry refuses to start on its next
restart, because the path in `REGISTRY_AUTH_HTPASSWD_PATH` is gone.

### `proxy-config` — lifts nginx-proxy's request body limit

nginx-proxy emits no `client_max_body_size` of its own, so every vhost inherits
nginx's 1m default. A docker image layer is far larger than that, which means a
registry behind an untouched nginx-proxy fails every `docker push` with a 413
before a single layer lands. There is no environment variable on the proxy for
this.

The supported way to patch a single vhost is a server-level snippet named after
the hostname in nginx-proxy's `vhost.d` directory, so `proxy-config` writes
`client_max_body_size 0;` and `proxy_read_timeout 900;` to
`/etc/nginx/vhost.d/${REGISTRY_DOMAIN}`. That directory is the `nginx-vhost`
volume owned by the **proxy-ssl** project, declared external here as
`proxy-vhost` and defaulting to proxy-ssl's usual `proxy_nginx-vhost` name —
override `PROXY_VHOST_VOLUME` if that project runs under a different `-p` on
the host.

The ordering matters and is the reason for the `depends_on`: docker-gen
regenerates the proxy config when it sees the registry container appear, and it
only picks the snippet up if the file already exists at that moment.

This is the one place where the registry project reaches into another project's
volume. It stays here rather than in proxy-ssl because the limit is a registry
requirement — no other vhost on any host wants an unbounded body size.
