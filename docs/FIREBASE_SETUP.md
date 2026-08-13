# Firebase setup for Frappe Push Relay

This guide explains how to create the Firebase credentials required by a **Local** Frappe Push Relay site.

A site in **Remote** mode does **not** need Firebase credentials. It uses the Firebase project configured on its relay host.

## What you need

A Local relay requires three groups of values:

1. **Firebase Web App configuration** — public configuration returned to browser/PWA clients.
2. **VAPID public key** — used by Firebase Cloud Messaging for Web Push.
3. **Firebase Admin SDK service-account JSON** — private server credential used by Frappe Push Relay to send through FCM.

> Never commit the service-account JSON to Git, paste it into an issue, or expose it through a public API.

## 1. Create a Firebase project

1. Open the Firebase Console and sign in.
2. Choose **Create a project**.
3. Enter a project name, for example `frappe-push-relay`.
4. Complete the project creation wizard. Google Analytics is optional for push delivery.

Official reference: https://firebase.google.com/docs/web/setup

## 2. Register a Firebase Web App

1. Open the Firebase project.
2. From **Project Overview**, choose the **Web** (`</>`) app icon. If an app already exists, use **Add app**.
3. Give it a nickname such as `Frappe Push Relay`.
4. Choose **Register app**.
5. Firebase displays a `firebaseConfig` object. Keep this page open or return later through **Project settings > General > Your apps**.

It looks similar to:

```javascript
const firebaseConfig = {
  apiKey: "...",
  authDomain: "example.firebaseapp.com",
  projectId: "example",
  storageBucket: "example.firebasestorage.app",
  messagingSenderId: "1234567890",
  appId: "1:1234567890:web:abcdef",
  measurementId: "G-ABCDEFG" // optional
};
```

These are web-client values, not the private Firebase Admin credential.

Official reference: https://firebase.google.com/docs/web/setup

## 3. Enable the FCM Registration API

Firebase Cloud Messaging for Web uses the **FCM Registration API** (`fcmregistrations.googleapis.com`) to register each browser installation with FCM.

1. Open **Google Cloud Console > APIs & Services > Library** for the same project.
2. Search for **FCM Registration API**.
3. Make sure the API is **Enabled**.
4. If the Firebase Web API key has **API restrictions**, make sure **FCM Registration API** is included in its allowed APIs.
5. If the key has **Website restrictions**, make sure every hostname that will run the browser client is allowed. Include your staging/development hostname when testing.

Firebase says new projects adding the FCM SDK normally have this API enabled automatically, but it should still be verified when browser registration returns an authentication or registration error.

Official references:
- https://firebase.google.com/docs/cloud-messaging/web/get-started
- https://firebase.google.com/docs/projects/api-keys

## 4. Generate the VAPID public key

1. Open **Project settings** in the Firebase Console.
2. Open the **Cloud Messaging** tab.
3. Find **Web configuration**.
4. Under **Web Push certificates**, choose **Generate Key Pair**.
5. Copy the generated **public key**.

Save only that public key in **Push Relay Settings > VAPID Public Key**. The relay does not ask you to paste a VAPID private key.

Official reference: https://firebase.google.com/docs/cloud-messaging/web/get-started

## 5. Generate the Firebase Admin SDK service-account JSON

1. Open **Project settings** in the Firebase Console.
2. Open the **Service accounts** tab.
3. In **Firebase Admin SDK**, choose **Generate New Private Key**.
4. Confirm **Generate Key**.
5. Firebase downloads a JSON file. Store that downloaded file securely.

Open the downloaded file in a text editor and copy the **entire JSON document**, including the opening and closing braces. Paste it into **Push Relay Settings > Firebase Service Account JSON**.

Frappe Push Relay stores this JSON text in one Frappe `Password` field and reads it server-side when initializing the Firebase Admin SDK. Do not split the service-account JSON into the Web App fields.

Official reference: https://firebase.google.com/docs/admin/setup

## 6. Enter the values in Frappe Push Relay

On the **Local relay site**, open **Push Relay Settings**, set **Push Mode** to `Local`, then map the Firebase values as follows:

| Push Relay field | Firebase source |
| --- | --- |
| Firebase Project ID | `firebaseConfig.projectId` |
| Firebase API Key | `firebaseConfig.apiKey` |
| Firebase Auth Domain | `firebaseConfig.authDomain` |
| Firebase Storage Bucket | `firebaseConfig.storageBucket` |
| Messaging Sender ID | `firebaseConfig.messagingSenderId` |
| Firebase App ID | `firebaseConfig.appId` |
| Measurement ID | `firebaseConfig.measurementId` if present |
| VAPID Public Key | Cloud Messaging > Web Push certificates > public key |
| Firebase Service Account JSON | Entire contents of the downloaded Admin SDK private-key JSON file |

The Web App configuration and VAPID public key are client-facing configuration. The **service-account JSON is private** and must stay server-side.

Frappe Push Relay keeps Frappe's compatibility parameter name `fcm_token`, but treats the stored value as an opaque Firebase registration identifier. Current Frappe application clients may supply an FCM registration token, while Firebase's APIs continue evolving; the relay does not infer identity or authorization from the identifier itself.

## 7. Configure relay hosting if other Frappe sites will use it

On the Local relay site:

1. Enable **Allow Other Sites To Use This Relay**.
2. Keep **Registration Policy = Approval Required** for an internet-facing relay unless automatic client enrollment is intentionally required.
3. Use the site's normal HTTPS base URL as the relay address. Frappe Push Relay automatically synchronizes this value to `push_relay_server_url` in `site_config.json`.

A Remote site should use **Push Mode = Remote** and point at the Local relay site's normal HTTPS URL. Saving the settings automatically synchronizes its `push_relay_server_url` as well. Do not copy Firebase credentials to Remote sites.

## How the service-account JSON is stored

Frappe Push Relay does **not** create one DocField for every property in the service-account JSON. The complete JSON text is saved in the single `Firebase Service Account JSON` field, whose Frappe field type is `Password`.

The relay retrieves it server-side with Frappe's password API, parses the JSON, and supplies it to the Firebase Admin SDK. It is never included in the public Firebase configuration endpoint.

## Security notes

- Treat the downloaded service-account JSON as a private key.
- Do not commit it to this repository or any other repository.
- Do not place it in browser JavaScript or return it from an API.
- Only trusted administrators should be able to change **Push Relay Settings**.
- If a service-account key is exposed, revoke/delete that key in Google Cloud/Firebase and generate a replacement.
- Use HTTPS for production and staging sites receiving Web Push. Firebase Cloud Messaging for web relies on browser service-worker/push security requirements.

## Troubleshooting

If browser push registration fails, verify the Web App configuration and VAPID public key came from the **same Firebase project** as the service-account JSON. Also verify the site is being served in a browser environment that permits service workers and Web Push.

If the browser receives `401 UNAUTHENTICATED` from `fcmregistrations.googleapis.com`, first re-check the **VAPID public key**. It must be the public key shown for this same Firebase project under **Cloud Messaging > Web configuration > Web Push certificates**. A structurally valid but mismatched VAPID key can prevent browser registration even when the Web App config and Admin SDK credential are correct.

As a diagnostic only, Firebase's JS SDK can use its built-in default VAPID key when no `vapidKey` is supplied. If registration works without the custom key but fails with it, replace the configured VAPID key with the correct project Web Push certificate. Do not rely on the default key as the final production configuration: Firebase recommends a generated/imported project key, and some push services require a non-default VAPID key.

If VAPID is correct and registration still fails, verify the **FCM Registration API** is enabled for the project and review the Firebase Web API key in Google Cloud Console. If that key is restricted by API, its allowlist must include `fcmregistrations.googleapis.com`. For a development hostname, also verify any Website restrictions allow that hostname.

For FCM's current web setup requirements, see:

- https://firebase.google.com/docs/cloud-messaging/web/get-started
- https://firebase.google.com/docs/web/setup
- https://firebase.google.com/docs/admin/setup
