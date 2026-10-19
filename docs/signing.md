# Stable development signing: setup boundary

Run `sh scripts/check-signing.sh`. It only lists available code-signing identities and whether `SECOND_BRAIN_SIGNING_IDENTITY` is configured. It does not create private keys, modify certificate trust, reset privacy permissions or sign anything.

On the development Mac, the check found **zero valid identities on 19 October 2026**. The user explicitly chose **Keep ad-hoc signing for now** on 19 October 2026. Stable signing is deliberately deferred; no Keychain changes were made. A stable identity must be configured in the macOS login keychain using your chosen Apple development/signing setup. Certificate creation and trust changes require you to review them in macOS; the project does not silently alter that security boundary.

Once a valid identity exists, build from the repository with:

```sh
SECOND_BRAIN_SIGNING_IDENTITY="Your exact local identity name" sh scripts/build-app.sh
```

Keep the bundle ID and identity stable across builds. Grant Screen Recording permission to that app through macOS System Settings. A stable identity reduces identity churn; it does not guarantee that macOS never asks again. Ad-hoc signing remains available for a local build and CI, with an explicit warning. Never commit a certificate's private key or signing password.
