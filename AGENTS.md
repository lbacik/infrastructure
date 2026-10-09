# Repository guidance

## Purpose and layout

This repository contains environment-agnostic Docker Compose projects. Each
top-level project directory normally contains:

- `compose.yaml` as the base definition;
- `env.example`, documenting every environment variable consumed by its compose
  files; and
- optional layered files such as `compose.override.yaml`, `compose.local.yaml`,
  or `compose.public.yaml`.

Keep host-specific populated env files, credentials, IP addresses, and secrets
in the separate `configurations/` repository. Do not add real `.env` files or
secrets here.

`vpn/` is the exception: it also includes `vpn/bin/ovpn.sh`, a provisioning
script that runs outside Compose. Its generated `config.ovpn` must remain
untracked.

## Editing Compose projects

- Preserve the raw Docker Compose deployment convention documented in
  `README.md`; do not introduce wrapper scripts unless explicitly requested.
- Treat `env.example` as the public interface for a project. When a compose
  file adds, removes, or renames a variable, update the matching template in
  the same change.
- Make optional deployment shapes explicit in a separate compose file, layered
  with `-f` in addition to (not instead of) `compose.yaml`.
- Keep service, volume, network, and container names stable unless a migration
  is part of the requested work. Other projects and deployed hosts can depend
  on them.
- Shared Docker networks are external. Do not replace them with project-local
  networks without confirming the cross-project impact.
- Use an explicit Compose project name (`-p <project>`) when providing deploy
  commands. Never rely on `COMPOSE_PROJECT_NAME` from an env file.

## Safety

- Do not commit credentials, generated certificates, populated env files, or
  other host-specific configuration.
- Be especially cautious with external volumes and one-shot setup containers:
  their outputs may be required by long-running services.
- Do not delete or overwrite existing worktree changes that are unrelated to
  the requested task.

## Validation

For a changed project, validate the relevant Compose shape before handoff:

```bash
docker compose \
  --project-directory <project> \
  -f <project>/compose.yaml \
  [ -f <project>/<extra-compose-file> ] \
  --env-file <path-to-non-secret-test-env> \
  -p <project> \
  config
```

Use a safe, non-secret env file for validation. If no usable values are
available locally, perform static review and state that runtime Compose
validation was not run.
