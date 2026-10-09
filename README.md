# infrastructure monorepo

Environment-agnostic Docker Compose projects. Each top-level directory is one
project: a `compose.yaml`, optionally an extra compose file layered on top
(`compose.override.yaml` / `compose.local.yaml`), and an `env.example`
template listing every variable that project's compose file(s) expect.

Real, populated per-host env files (secrets, IPs, credentials) live in a
**separate** repo, `configurations/`, never here — see "Configuring a new
host" below.

## Deploy convention

No wrapper script. Every project is deployed with the same raw `docker
compose` invocation:

```bash
docker compose \
  --project-directory monorepo/<project> \
  -f monorepo/<project>/compose.yaml \
  [-f monorepo/<project>/<extra-compose-file>] \
  --env-file configurations/<host>/<project>.env \
  -p <project> \
  up -d
```

Notes:
- **`-p <project>` is always passed explicitly.** Never rely on
  `COMPOSE_PROJECT_NAME` from the env file — a stale value there silently
  changes container names and breaks anything that references them by name
  (this already happened once: `dns`/`jobs`, see the `dns` project's
  `container_name:` pin).
- `--env-file` is omitted only for projects with no env needs
  (`nginx-mngm`).
- Projects with an extra compose file layered via `-f` (pass it in addition
  to `compose.yaml`, not instead of):
  - `elastic/compose.public.yaml` — publishes Kibana through proxy-ssl
    (`KIBANA_DOMAIN`, `LETSENCRYPT_EMAIL`); Elasticsearch stays unpublished.
  - `litellm/compose.local.yaml` — publishes the gateway on host loopback
    (`HOST_PORT`) for clients run outside docker; it is otherwise reachable
    only on the shared network.
  - `postgresql/compose.override.yaml` — adds host port bindings
    (`HOST`/`PORT`/`PGV_PORT`); only needed if the host exposes postgres
    outside the shared docker network.
  - `redis/compose.local.yaml` — local-only overrides.
  - `registry/compose.override.yaml` — pins a static `ipv4_address`/alias
    on the shared network (`REGISTRY_IP`/`REGISTRY_ALIAS`); only needed on
    hosts that require a fixed registry IP (currently just `ale`).
  - `registry/compose.public.yaml` — turns the registry into an
    internet-facing one: htpasswd auth (`REGISTRY_USER`/`REGISTRY_PASSWORD`)
    plus the `client_max_body_size 0` snippet nginx-proxy needs before a
    layer push can succeed. Used on `rum`, where the registry stands in for
    ghcr.io on private repositories. Mutually independent of
    `compose.override.yaml`, but the two have never been combined. It also
    brings two one-shot containers that stay behind as `Exited (0)` — see
    `registry/README.md`, the one project here with its own README.
- Running a second instance of a project on the same host (e.g. a second
  mysql or proxy-ssl for local testing) uses a distinct `-p` and its own
  env file: `-p mysql-5 --env-file configurations/local/mysql-5.env`,
  `-p proxy-test --env-file configurations/local/proxy-ssl-test.env`.
- `nginx-proxy-path` is not pinned to any particular host — it's a
  per-target preview proxy that can run wherever a target needs one. Its
  configs live at `configurations/nginx-proxy-path/<domain>.env` instead of
  under a host directory.

## Configuring a new host

```bash
mkdir -p configurations/<host>
cp monorepo/<project>/env.example configurations/<host>/<project>.env
# fill in real values
```

The template lives with the project (in this repo) rather than in
`configurations/` because it's part of the project's interface — it stays
in sync with `compose.yaml` in the same commits.

## Running against a remote host

For remote hosts (`rpi5`, `gin`, `ale`, `ovh`, `rum`), either:
- rsync this repo plus that host's `configurations/<host>/` slice to the
  machine and run the command over `ssh <host> 'cd ... && docker compose ...'`, or
- point a local `docker context` at the host's SSH endpoint and run
  `docker --context <host> compose ...` from here.

Neither is picked for you — use whichever fits the host.

## vpn exception

`vpn/` mixes a compose service with a bespoke provisioning script,
`vpn/bin/ovpn.sh` (cert/client management, runs outside compose). The
script travels with the project here. It writes `config.ovpn` to its
current directory as a generated artifact — that file is gitignored (see
`.gitignore`) and is never committed to either repo.

## Projects

`beszel`, `dns`, `elastic`, `filebeat`, `jobs`, `litellm`, `listmonk`,
`mailcatcher`, `mariadb`, `minio`, `mongodb`, `mysql`, `nginx-mngm`,
`nginx-proxy-path`, `open-hands`, `pact-broker`, `portainer`,
`postgresql`, `proxy-ssl`, `rabbitmq`, `redis`, `registry`, `umami`, `vpn`,
`zabbix`.
