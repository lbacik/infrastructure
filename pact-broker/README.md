# Pact Broker

This project runs the open-source Pact Broker against the existing `psql`
service from the `postgresql` project. The Broker stores consumer-provider
contracts, verification results, and release/deployment metadata in its own
database and role on that PostgreSQL instance.

It is designed for the repository's `proxy-ssl` deployment shape: both services
join the same external Docker network, and `nginx-proxy` routes HTTPS traffic to
the Broker's internal port 9292. There is intentionally no host port binding.

## Configure and deploy

Create `configurations/<host>/pact-broker.env` from `env.example`. Set
`PACT_BROKER_DATABASE_HOST` to the `PSQL_ALIAS` used by the existing
`postgresql` deployment, and use a dedicated `pact_broker` database and role.
Use a stable HTTPS name for both `PACT_BROKER_DOMAIN` and
`PACT_BROKER_BASE_URL`, for example `https://pact.example.com`. Set distinct,
strong credentials for the broker's read/write CI account and read-only
developer account. The compose definition enables basic auth automatically
when those credentials are supplied.

Before starting Pact Broker, create its database and role once through the
existing PostgreSQL instance (replace the password with the value in the host
Pact Broker env file):

```sql
CREATE ROLE pact_broker WITH LOGIN PASSWORD 'CHANGE_ME';
CREATE DATABASE pact_broker OWNER pact_broker;
```

Deploy it after `postgresql` and `proxy-ssl` are running on the same `NETWORK`:

```bash
docker compose \
  --project-directory monorepo/pact-broker \
  -f monorepo/pact-broker/compose.yaml \
  --env-file configurations/<host>/pact-broker.env \
  -p pact-broker \
  up -d
```

Check the unauthenticated liveness endpoint (the UI/API require credentials):

```bash
curl --fail https://pact.example.com/diagnostic/status/heartbeat
```

## Start using it

1. In each consumer test pipeline, generate Pact files and publish them with a
   unique consumer application version, the commit SHA, and its branch. Give
   the pipeline the read/write credentials and `PACT_BROKER_BASE_URL`.
2. In each provider pipeline, fetch and verify the relevant pacts, then publish
   the verification result using the provider version and branch.
3. Record releases and deployments and make `can-i-deploy` a required release
   gate. This connects the contract result to the version and environment that
   are actually being shipped.

Use a Pact language library or the Pact Broker CLI supported by each service's
runtime. Clients can normally read `PACT_BROKER_BASE_URL`,
`PACT_BROKER_USERNAME`, and `PACT_BROKER_PASSWORD` from their CI environment;
developers should use the read-only credentials.

## Operational notes

- PostgreSQL is required for production; SQLite is only suitable for a local
  spike because it cannot safely handle concurrent requests.
- Pact Broker applies backwards-compatible database migrations on startup. Do
  not downgrade the broker image without following Pact's migration rollback
  guidance.
- The public heartbeat is deliberately enabled so Docker and load-balancer
  probes work while basic authentication protects the broker UI and API.
- Back up the existing PostgreSQL data volume before upgrades and keep the
  Broker image version pinned in the host env file.

## References

- [Pact Broker Docker image](https://docs.pact.io/pact_broker/docker_images/pactfoundation)
- [Pact Broker settings](https://docs.pact.io/pact_broker/configuration/settings)
- [Pact Broker set-up checklist](https://docs.pact.io/pact_broker/set-up-checklist)
