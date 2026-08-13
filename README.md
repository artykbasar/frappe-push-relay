# Frappe Push Relay

Self-hosted Firebase Cloud Messaging relay for Frappe Framework.

Frappe Push Relay implements the `notification_relay.api.*` contract used by Frappe's `PushNotification` class, so sites can use their own Firebase project instead of depending on a hosted relay service.

## Modes

- **Local** — this site owns the Firebase Web/App credentials and sends notifications through FCM.
- **Remote** — this site has no Firebase credentials; it uses another Frappe site running this app in Local mode.

A Local site can optionally enable **Allow Other Sites To Use This Relay**. Remote clients are isolated by relay site, project name, user, device and topic.

## Compatibility

The app provides compatibility endpoints for Frappe's current `notification_relay.api.*` calls and automatically publishes `push_relay_server_url` through Frappe boot data.

Validated during development against:

- Frappe Framework 17.x develop `PushNotification`
- Frappe HR (`project_name="hrms"`) push contract
- Frappe Suite Mail/Calendar (`project_name="mail"`) push contract
- Firebase Web Messaging token registration and Firebase Admin SDK delivery

Applications with a custom push implementation should still be tested against their own client/service-worker code.

## Installation

```bash
bench get-app https://github.com/<owner>/frappe-push-relay
bench --site your-site.example.com install-app frappe_push_relay
bench --site your-site.example.com migrate
```

Then open **Push Relay Settings**.

### Local mode

1. Select **Local**.
2. Enter the Firebase Web App configuration, VAPID public key and Firebase Admin service-account JSON.
3. Use **Test Firebase Connection**.
4. If other sites will use this relay, enable **Allow Other Sites To Use This Relay**.
5. Keep **Registration Policy = Approval Required** for internet-facing hosts unless automatic enrollment is intentional.

See [Firebase Setup Guide](docs/FIREBASE_SETUP.md) for the Firebase-side setup.

### Remote mode

1. Install Frappe Push Relay on the client site.
2. Select **Remote**.
3. Set **Remote Relay URL** to the Local relay site's HTTPS base URL.
4. Save. Frappe performs its normal callback registration when push is first used.
5. If the host requires approval, approve the pending **Push Relay Site** there; the client retries the verified registration handshake on its next push operation.

The app automatically synchronizes `push_relay_server_url` in the site's `site_config.json`. No manual `bench set-config push_relay_server_url ...` command is required.

## Security and operations

- Production relay URLs must use HTTPS. Plain HTTP is accepted only for localhost development mode.
- Firebase service-account JSON is stored in a Frappe `Password` field and is never returned by the public config endpoint.
- The public `get_config` endpoint exposes only Firebase browser configuration and the VAPID public key; this information is intentionally client-facing.
- Remote client API credentials are bound to one approved relay-site identity. Disabling relay hosting, changing out of Local mode, disabling a site, or rejecting a site blocks that credential from relay APIs.
- Registration callbacks require the standard Frappe auth-webhook route, public-address validation, no redirects, bounded responses, rate limiting and verified callback-host binding.
- Device registrations, topics and subscriptions are isolated by relay site and project. Device registration identifiers are treated as opaque Firebase identifiers.
- Delivery payloads pass through the relay host and Firebase/Google infrastructure. Delivery logs keep status/count/error metadata, not notification bodies or Firebase credentials.
- Run normal Frappe workers and the scheduler. Push sends are queued on the `short` queue; cleanup jobs run daily.

## Stored records

The app keeps six DocTypes, each with a distinct purpose:

- **Push Relay Settings** — Local/Remote mode and Firebase/relay configuration.
- **Push Relay Site** — approved remote relay clients and their API-user binding.
- **Push Device** — per-site/project/user Firebase registration identifiers.
- **Push Topic** — Frappe-compatible logical topics.
- **Push Topic Subscription** — user membership in those topics.
- **Push Delivery Log** — operational delivery outcome metadata.

## License

MIT
