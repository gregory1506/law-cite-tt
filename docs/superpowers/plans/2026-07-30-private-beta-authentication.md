# LawCite TT Private Beta Authentication Plan

**Date:** 2026-07-30

**Status:** Ready for implementation

**Production frontend:** `https://law-cite-tt.gjo-ai.workers.dev`

**Production API origin:** `https://srv1629323.hstgr.cloud`

## Objective

Secure the existing LawCite customer application for an invite-only private
beta without purchasing a custom domain or building a first-party account
system.

The private beta will use Cloudflare Access on the existing `workers.dev`
hostname. Invited users will authenticate by email one-time PIN. All browser API
requests will pass through the Cloudflare Worker, and FastAPI will independently
verify the signed Cloudflare Access token before serving protected data.

## Current State

- The Svelte frontend is deployed as static Worker assets.
- The frontend login is a UI-only stub backed by a token in `localStorage`.
- The browser calls the public Hostinger API directly.
- FastAPI does not authenticate or authorize API requests.
- CORS permits the production Worker hostname and local development origins.
- The Hostinger API is exposed through Traefik.
- Authentication, backend authorization, and rate limiting are the current
  release gate.

## Decisions

### Hostname

Continue using:

`https://law-cite-tt.gjo-ai.workers.dev`

Cloudflare Access supports protecting a `workers.dev` route directly. A custom
domain is therefore not required for the beta.

### Identity

Use Cloudflare Access with:

- Email one-time PIN authentication
- An explicit allowlist of invited email addresses
- Deny by default
- A 24-hour application session
- No LawCite passwords, password resets, or user database
- Cloudflare Zero Trust Free while the beta has no more than 50 users

### Request Path

Current:

```text
Browser -> Hostinger API
```

Target:

```text
Tester
  -> Cloudflare Access
  -> LawCite Worker
       -> static Svelte assets
       -> /api/* proxy
            -> Hostinger FastAPI
                 -> PostgreSQL
```

The Worker and API will enforce complementary security boundaries:

1. Cloudflare Access blocks unapproved users before the Worker runs.
2. The Worker proxies authenticated same-origin `/api/*` requests.
3. FastAPI verifies the signed Access JWT so the public Hostinger hostname
   cannot be used to bypass Cloudflare.

## Phase 1: Baseline and Rollback Preparation

1. Record the active Cloudflare Worker version.
2. Record the active Hostinger API image tag and Compose configuration.
3. Run the frontend and backend test suites.
4. Exercise the production health, chapter, search, lookup, and citation
   endpoints.
5. Save the commands required to restore the recorded Worker version and API
   image.

No database schema or corpus changes are required.

## Phase 2: Convert the Worker to a Same-Origin Gateway

Update `citation-tool/wrangler.toml` and add a Worker entry point that:

1. Sends non-API requests to the existing static asset binding.
2. Proxies `/api/*` requests to the configured Hostinger API origin.
3. Accepts only the intended HTTP methods.
4. Preserves query strings and required response headers.
5. Explicitly forwards the Cloudflare Access JWT assertion.
6. Removes client-supplied forwarding and internal authentication headers that
   must not be trusted.
7. Applies a bounded upstream timeout and returns a controlled gateway error
   when the API is unavailable.
8. Does not expose backend secrets or detailed upstream errors to the browser.

Configure the production API origin as a Worker environment variable. It is not
a secret, but keeping it out of application code makes local and production
configuration explicit.

Update `citation-tool/src/lib/api.js` so production calls use relative paths:

```text
/api/stats
/api/chapters
/api/search/grouped
/api/lookup
/api/citations/resolve
```

Local development may continue to use a configured development API origin.

## Phase 3: Replace the Frontend Authentication Stub

Remove the localStorage session implementation from:

- `citation-tool/src/lib/auth.js`
- `citation-tool/src/App.svelte`

The frontend must not decide whether a user is authenticated. Cloudflare Access
owns that decision before serving the application.

Add:

1. A small identity request to Cloudflare's Access identity endpoint when the
   app needs the signed-in user's email.
2. A signed-in indicator based on verified Access identity data.
3. A logout action that uses the Cloudflare Access logout endpoint.
4. Friendly handling for an expired session or an API `401`.

Do not store the Access JWT in `localStorage` or expose it to application code
unless strictly necessary.

## Phase 4: Enforce Authorization in FastAPI

Add a FastAPI authentication dependency or middleware that:

1. Requires the Cloudflare Access JWT assertion on protected API routes.
2. Loads signing keys from the configured Cloudflare Access JWKS endpoint.
3. Caches signing keys with a bounded refresh period.
4. Verifies the JWT signature.
5. Verifies the expected issuer.
6. Verifies the application audience (`aud`).
7. Verifies expiry and not-before claims.
8. Rejects a missing or invalid token with `401`.
9. Records only safe authentication metadata in logs; never log the raw JWT.

Configuration must be supplied through environment variables:

- Cloudflare Access team/domain identifier
- Expected Access application audience
- Authentication enforcement flag for controlled rollout

Apply authentication to all customer data routes. Decide separately how
deployment monitoring reaches `/api/health`:

- Preferred: require a Cloudflare Access service token for external health
  checks.
- Local container and deployment checks may use an internal or loopback health
  endpoint.

After the gateway is live, tighten CORS. Normal production browser requests
will be same-origin and should not require broad cross-origin permissions.
Local development origins may remain explicitly allowed.

## Phase 5: Enable Cloudflare Access

In Cloudflare:

1. Open **Workers & Pages**.
2. Select the `law-cite-tt` Worker.
3. Open **Settings -> Domains & Routes**.
4. Enable Cloudflare Access for the `workers.dev` route.
5. Configure email one-time PIN as the identity provider.
6. Create a deny-by-default Access application policy.
7. Add an Allow rule containing only approved beta email addresses.
8. Use a 24-hour session duration.
9. Protect preview deployments as well, or disable preview URLs.
10. Start with the owner's email before adding testers.

The invite list remains operational configuration and must not be committed to
the repository.

## Phase 6: Rate Limiting

Add Traefik or application-level limits that protect the VPS while preserving
normal legal research workflows.

Initial policy:

- A general per-client request limit for ordinary reads
- A stricter limit for vector and hybrid searches
- A small burst allowance for initial page loading
- `429 Too Many Requests` responses with a clear retry interval
- Logs and metrics sufficient to tune the limits after real beta usage

Where feasible, rate-limit using authenticated identity in addition to source
IP. IP-only limits can incorrectly combine users behind the same office
network.

## Phase 7: Automated Tests

### Worker and frontend

- Static assets still resolve through the Worker.
- `/api/*` requests are proxied to the configured API origin.
- Query strings are preserved.
- The Access assertion is forwarded.
- Spoofable internal headers are stripped.
- Upstream failures return controlled errors.
- The frontend uses same-origin API paths.
- The localStorage stub is gone.
- Logout and expired-session behavior are covered.

### FastAPI

- Missing JWT returns `401`.
- Malformed JWT returns `401`.
- Invalid signature returns `401`.
- Expired token returns `401`.
- Wrong issuer returns `401`.
- Wrong audience returns `401`.
- A valid Access token reaches protected endpoints.
- Signing-key refresh behavior is covered.
- Authentication logs do not expose tokens.
- Existing search, lookup, chapter, stats, and citation tests remain green.

## Phase 8: Deployment Sequence

Use this order to avoid locking out the application:

1. Complete and pass all local tests.
2. Deploy the Worker gateway while the backend remains in its current state.
3. Confirm all application workflows through same-origin `/api/*`.
4. Enable Cloudflare Access with only the owner's email allowed.
5. Confirm login, identity, API proxying, and logout.
6. Confirm the Access JWT reaches the API through the Worker.
7. Deploy FastAPI JWT verification with enforcement enabled.
8. Confirm direct unauthenticated API access now returns `401`.
9. Apply and tune rate limiting.
10. Add beta tester emails after the complete path passes verification.

Record the deployed Worker version and backend image after each successful
production change.

## Production Acceptance Checks

The beta is ready only when all of the following pass:

- An anonymous visitor is redirected to Cloudflare authentication.
- The owner's approved email receives a PIN and can enter.
- A non-allowlisted email is denied.
- Research, chapter browsing, lookup, and citation resolution work.
- Direct requests to the Hostinger API without a valid Access JWT return `401`.
- Forged, expired, and wrong-audience tokens are rejected.
- Logout removes access and requires authentication again.
- Desktop and mobile flows work.
- Rate-limited requests receive controlled `429` responses.
- Frontend and backend automated tests pass.
- Rollback instructions and deployed version identifiers are recorded.

## Rollback

If the authentication rollout causes a production failure:

1. Restore the previously recorded backend image.
2. Restore the previously recorded Worker version.
3. Disable Cloudflare Access on the `workers.dev` route if Access itself is the
   failure point.
4. Re-run the original production smoke checks.

Do not delete the Access application or its policies during rollback; disabling
the route is faster and preserves configuration for diagnosis.

Because this rollout does not modify the database, rollback does not require a
database restore.

## Required Input Before Final Activation

- The owner's email address for the initial Allow policy
- The approved tester email list when invitations are ready
- The Cloudflare Access application audience and team identifier generated
  during setup

## Deferred Until After Beta

- Purchasing `lawcite.tt`
- Migrating to `app.lawcite.tt`
- First-party accounts and password management
- Self-service registration
- Billing and subscriptions
- Roles beyond the beta allowlist
- Long-term user-profile storage
