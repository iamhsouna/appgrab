# DubaiNow — Hardcoded Information Extraction

Extracted from:

- `com.deg.mdubai.xapk` — Android App Bundle split set (`com.deg.mdubai`, version `14.6.29`, versionCode `514`)
- `com.deg.mdubai_619712783_14.6.30.ipa` — iOS App Store IPA (`com.deg.mdubai`, version `14.6.30`)

> Methodology: unzip → `apktool` (Android manifest/resources) → `strings`/pattern mining of the Flutter AOT snapshot `libapp.so` (Android, **not** obfuscated) → plist/entitlement parsing of the IPA. The iOS Mach-O binaries (`DubaiNow`, `App.framework/App`, all `.framework`s and `.appex`es) are FairPlay-encrypted (`cryptid=1`), so their code strings are not readable; the Flutter asset bundle and all property lists are plaintext and were parsed. Android and iOS share the same Dart codebase, so app constants mined from Android apply to both.

---

## 1. Application metadata

| Field | Android (XAPK) | iOS (IPA) |
| --- | --- | --- |
| App name | DubaiNow | DubaiNow |
| Bundle / package | `com.deg.mdubai` (QA: `com.deg.mdubai.qa`, dev: `com.deg.mdubai.dev`) | `com.deg.mdubai` |
| Version | `14.6.29` (code `514`) | `14.6.30` (build `1`) |
| Min OS | minSdk `24` / targetSdk `36` | iOS `14.0` |
| Vendor | Digital Dubai / Dubai eGovernment Department | same |
| Apple item ID | — | `619712783` (artistId `567993892`) |
| Download account (in `iTunesMetadata.plist`) | — | `iamhsouna@gmail.com` |
| Android runtime protection | `com.pairip.application.Application` + `libpairipcore.so` (Google Play PairIP) | FairPlay DRM (`cryptid=1`) |
| Cleartext traffic | `android:usesCleartextTraffic="true"`, `requestLegacyExternalStorage="true"` | `NSAllowsArbitraryLoads=true`, `NSAllowsArbitraryLoadsInWebContent=true` |

---

## 2. API keys, secrets and third-party credentials

### Google / Firebase

| Value | Purpose | Source |
| --- | --- | --- |
| `AIzaSyA1gnBLhO6rxYuFFeJLGaO2WHECYcN8eNk` | **Google Maps Android API key** | `AndroidManifest.xml` → `com.google.android.geo.API_KEY` |
| `AIzaSyCBzCxDSiSZp52GmdEbZaecxNt_haNhqqY` | Firebase Android API key / crash-reporting key | `res/values/strings.xml` (`google_api_key`, `google_crash_reporting_api_key`) |
| `1:364553237282:android:7ca382e539b9bfaa402b7b` | Firebase Android App ID | `strings.xml` (`google_app_id`) |
| `364553237282` | Firebase sender ID (Android) | `strings.xml` (`gcm_defaultSenderId`) |
| `dubai-now-274f5` | Firebase project ID (prod) | `strings.xml` (`project_id`) |
| `dubai-now-274f5.firebasestorage.app` | Firebase storage bucket | `strings.xml` (`google_storage_bucket`) |
| `AIzaSyBkiPWSjDRyWTs2iHpet9BWKPnwFJ7AXHE` | Firebase iOS API key (prod) | `GoogleService-Info.plist`, `GoogleService-Info-PROD.plist` |
| `1:364553237282:ios:1e96b807a304b452402b7b` | Firebase iOS App ID (prod) | same |
| `364553237282` / `dubai-now-274f5` / `dubai-now-274f5.firebasestorage.app` | Sender ID / project / bucket (prod) | same |
| `AIzaSyChA5-KMZ8DNoY0QOl2x7XQaCk5WfuW6rE` | Firebase iOS API key (QA/DEV) | `GoogleService-Info-QA.plist`, `GoogleService-Info-DEV.plist` |
| `1:648168323491:ios:799a13555d82df74914216` | Firebase iOS App ID (QA/DEV) | same |
| `648168323491` | Firebase sender ID (QA/DEV) | same |
| `digitaltribe-7242b` / `https://digitaltribe-7242b.firebaseio.com` | Firebase project + Realtime DB (QA/DEV) | same |
| `648168323491-ku4chu32egh4kkh9trmepdookmse1ddt.apps.googleusercontent.com` | OAuth client ID (iOS, QA/DEV) | same |
| `648168323491-kovtolin84b1rfp34j94kvlckdf5uie9.apps.googleusercontent.com` | OAuth Android client ID (QA/DEV) | same |
| `com.googleusercontent.apps.648168323491-ku4chu32egh4kkh9trmepdookmse1ddt` | Reversed client ID URL scheme | same |

### Monitoring / analytics

| Value | Purpose | Source |
| --- | --- | --- |
| `https://2332ab27dd8fa9e717eb39c3e7ff6aeb@o4506652415754240.ingest.us.sentry.io/4507825079910400` | **Sentry DSN** (project `4507825079910400`, org `o4506652415754240`, region `us`) | Android `libapp.so` strings |
| `https://o4506652415754240.ingest.us.sentry.io` | Sentry ingest host | Android `libapp.so` strings |
| `https://api2.amplitude.com/2/httpapi`, `https://api2.amplitude.com/batch`, `https://api.eu.amplitude.com/2/httpapi`, `https://api.eu.amplitude.com/batch` | Amplitude SDK endpoints (key not extractable) | Android `classes*.dex` |
| `https://app.adjust.com`, `https://app.adjust.io`, `https://gdpr.adjust.com`, `https://gdpr.adjust.io` | Adjust SDK endpoints (app token not extractable) | Android `classes*.dex` |

### Native Android (Kotlin/Glance prayer-times widget)

Recovered by decompiling `classes7.dex` with `jadx` (`com.deg.mdubai.BuildConfig`):

| Value | Purpose | Source |
| --- | --- | --- |
| `4ddf08b337e86ea5ef0ea057f83d5bd4ebf9f3fb3a24f81935389e02093cf817` | **`PRAYER_TIMES_API_KEY`** — sent as the `X-API-Key` request header | `BuildConfig.PRAYER_TIMES_API_KEY` |
| `https://dubainowocp.dubai.ae/internal/gateway/api/services/` | `PRAYER_TIMES_BASE_URL` | `BuildConfig.PRAYER_TIMES_BASE_URL` |
| `GET islam/v2/prayer/time?month=&year=&cityid=` | Prayer-times endpoint (header `Content-Type: application/json`, `X-API-Key: <key>`) | `PrayerTimesApi` + `PrayerTimesNetworkModule` |

### PairIP integrity hashes (Android)

| Value | Purpose | Source |
| --- | --- | --- |
| `L84sBoVqKt1uy26jw/N0uU404apQUUcUfD02pU1MVGo=` | expected APK signing-cert SHA-256 (base64) | `com.pairip.SignatureCheck` |
| `Vn3kj4pUblROi2S+QfRRL9nhsaO2uoHQg6+dpEtxdTE=` | allowlisted signing-cert SHA-256 (base64) | `com.pairip.SignatureCheck` |

### APK signing certificate (extracted from the APK Signing Block v2)

| Field | Value |
| --- | --- |
| Subject / Issuer | `CN=MDubai, OU=Dubai Smart Gov, O=Dubai Smart Gov, L=Dubai, ST=UAE` |
| Serial | `1503511310` |
| Validity | 2013-10-22 → 2113-09-28 |
| SHA-256 | `2fce2c06856a2add6ecb6ea3c3f374b90e34e1aa505147147c3d36a54d4c546a` (matches `assetlinks.json`) |
| SHA-1 | `e3b505ff7ac6614fdd40cee5a7e4871cd279ac71` |

A second cert in the block is Google's Play signing cert (`CN=Android, O=Google Inc.`, SHA-256 `3257d599a49d2c961a471ca9843f59d341a405884583fc087df4237b733bbd6d`) — the app is additionally signed/rotated by Google Play.

### UAE Pass / identity (Dart snapshot)

| Value | Purpose |
| --- | --- |
| `dubainow_mobileapp_prod_v2` | **Candidate UAE Pass `clientID`** (production) |
| `dubai_nowtcmob_prod` | Secondary app/tenant identifier |
| `digitalid-users-ids` | UAE Pass scope / key name |
| `urn:uae:digitalid:profile:general`, `…:profileType`, `…:unifiedId`, `urn:digitalid:authentication:flow:mobileondevice`, `urn:safelayer:tws:policies:authentication:level:low` | UAE Pass `scope` / `acr_values` values |
| `uaepass://digitalid`, `uaepass://`, `uaepassqa://`, `uaepassstg://` | UAE Pass launch/deep-link schemes |
| `d4754b73-bc32-422f-b87c-464f89c99fa2` | Unidentified hardcoded UUID constant (others are placeholders such as `aaaaaaaa-…`) |

### Apple / store identifiers

| Value | Purpose | Source |
| --- | --- | --- |
| `PTEE8T35KX` | Apple Team ID (production) | iOS entitlements + `apple-app-site-association` |
| `X95CWGK9TY` | Apple Team ID (QA) | `apple-app-site-association` |
| `PTEE8T35KX.com.deg.mdubai` | Application identifier (production) | iOS entitlements |
| `merchant.ni.ae.gov.sdg`, `merchant.ni.ae.gov.sdg.production`, `merchant.ae.sdg.dubainow.staging` | Apple Pay merchant IDs | iOS entitlements (`com.apple.developer.in-app-payments`) |
| `aps-environment = production` | Push environment | iOS entitlements |
| `2F:CE:2C:06:85:6A:2A:DD:6E:CB:6E:A3:C3:F3:74:B9:0E:34:E1:AA:50:51:47:14:7C:3D:36:A5:4D:4C:54:6A` | Android signing cert SHA-256 (prod + QA) | `assetlinks.json` |

### Android build info (`BuildConfig`)

| Value | Purpose |
| --- | --- |
| `APPLICATION_ID = com.deg.mdubai`, `BUILD_TYPE = release`, `FLAVOR = prod` | Build flavor |
| `FLUTTER_BUILD_NAME = 14.6.29`, `FLUTTER_BUILD_NUMBER = 514`, `FLUTTER_BUILD_MODE = debug` | Version metadata |
| `FLUTTER_ROOT = /Users/ddadev2/development/flutter` | **Developer workstation path leak** |

> No AWS keys, JWTs, private keys, bearer tokens, Stripe keys or embedded TLS pinning certificates were found in plaintext. (`happinessMeterClientID` / `happinessMeterServiceProviderSecret` / `client_id` exist only as variable names in the Dart snapshot — their values come from runtime/remote config.)

---

## 3. URL schemes & deep links

### iOS (`Info.plist`)

- Custom scheme: `dubaiNow` (URL name `dubaiNow`, role Editor)
- Query schemes (`LSApplicationQueriesSchemes`): `sms`, `tel`, `esaad`, `googlechromes`, `comgooglemaps`, `uaepass`, `uaepassstg`, `uaepassqa`

### Android (`AndroidManifest.xml`)

- App Links (autoVerify): `https://dubainow.dubai.ae/`, `https://dubainow.go.link/`
- Custom scheme: `dubaiNow://success`, `dubaiNow://failure`
- Queried packages include UAE Pass (`ae.uaepass.mainapp`, `ae.uaepass.mainapp.stg`), Google Maps (`com.google.android.apps.maps`, `.mapslite`), Waze, Yandex, HERE, TomTom and many map apps.

### Other schemes hardcoded in the Dart code

- `happiness://done` (Happiness Meter callback)
- Map-launcher schemes: `waze://`, `yandexmaps://`, `yandexnavi://`, `mapsme://`, `citymapper://`, `here`/`share.here.com`, `amapuri://`, `baidumap://`, `qqmap://`, `kakaomap://`, `nmap://`, `tmap://`, `com.sygic.aura://`, `dgis://`, `copilot://`, `truck`/`petalmaps://`, `market://`, `tel://`
- `uaepass://`, `uaepassqa://`, `uaepassstg://`, `uaepass://digitalid`

### iOS associated domains / app groups (entitlements)

- `applinks:dubainow.dubai.ae`
- `applinks:dubainow.qa.dubai.ae`
- `applinks:dubainow.go.link`
- `applinks:dubainowqa.go.link`
- App group: `group.com.deg.mdubai`

### Android app groups (from Dart strings)

- `group.com.deg.mdubai`
- `group.com.deg.mdubai.qa`
- `group.com.deg.mdubai.dev`

---

## 4. Hardcoded endpoints, hosts and domains

### Base / environment hosts (Dart + config JSON)

| Host | Environment |
| --- | --- |
| `dubainow-core-gateway.dubai.ae` | Production gateway |
| `dubainow.dubai.ae` | Production app link |
| `dubainow-app.dubai.ae` | Production |
| `dubainowocp.dubai.ae` | Production OCP |
| `dubainow.qa.dubai.ae` / `dubainowocp.qa.dubai.ae` | QA |
| `apis.dubai.gov.ae` | Production API |
| `stg-apis.dubai.gov.ae` | Staging API |
| `api.dubai.gov.ae` | Shared API |
| `api.qa.dubai.gov.ae` | QA API |
| `daas-cp.dev.dubai.gov.ae` | Dev (DAAS control plane) |
| `unifyapps.digitaldubai.ae` / `unifyapps.qa.digitaldubai.ae` | UnifyApps |
| `id.uaepass.ae`, `stg-id.uaepass.ae`, `qa-id.uaepass.ae` | UAE Pass identity |
| `registration.uaepass.ae` | UAE Pass registration |
| `happinessmeter.dubai.gov.ae` | Happiness Meter |
| `mpay.dubai.ae` | Payment |
| `app.invest.dubai.ae` | Dubai Invest |
| `chat.dubai.ae` / `chat.qa.dubai.ae` | Chatbot |
| `www.digitaldubai.ae`, `www.rta.ae`, `www.salik.ae` | Public sites |
| `dubainow.go.link` | Branch/attribution link |

### Full URLs found

```
https://04.gov.ae/case-generate
https://apis.dubai.gov.ae/secure/sdg/dxbnw/configservice/1.0.0/api/services/cms/items
https://app.invest.dubai.ae/login
https://chat.dubai.ae/?source=dubainow
https://daas-cp.dev.dubai.gov.ae/
https://dubainow-core-gateway.dubai.ae/paperless-middleware/api/services
https://dubainow-core-gateway.dubai.ae/paperless-middleware/api/services/auth/oauth2
https://dubainow-core-gateway.dubai.ae/paperless-middleware/api/services/cms
https://dubainow-core-gateway.dubai.ae/paperless-middleware/api/services/cms/graphql
https://dubainow.dubai.ae
https://happinessmeter.dubai.gov.ae/HappinessMeter2/MobilePostDataService
https://id.uaepass.ae
https://mpay.dubai.ae/OnlinePaymentController/secureSignOn
https://registration.uaepass.ae/?
https://stg-id.uaepass.ae
https://qa-id.uaepass.ae
https://unifyapps.digitaldubai.ae/api-endpoint
https://unifyapps.qa.digitaldubai.ae/api-endpoint
https://www.digitaldubai.ae
https://www.salik.ae
https://dubainowocp.dubai.ae/internal/gateway/api/services/
```

### API paths (Dart snapshot)

```
/apis.dubai.gov.ae/secure/sdg/dxbnw/configservice/1.0.0/api
/dha/v1/sickleave/certificates
/dha/v1/sickleave/certificates/download
/dha/v1/sickleave/family-mrnr
/dubainow/paperless/5.0.0/api/entity/dld
/dxbnw/internal/dp/1.0.0/api/services/dp
/dxbnw/internal/generalservices/1.0.0/api/services/general
/dxbnw/internal/generalservices/1.0.0/api/services/general/uaepass/document-sign/token
/dxbnw/internal/pushnotificationapi/1.0.0/api/services/push-notification-api
/dxbnw/internal/userclassifications/1.0.0/api/services/user-classification
/dxbnw/mw-services/1.0.0/api/services/ext/mbrhe
/events-offers/v1/events/weekly
/external-integration/v1/unify/pod/details
/general/v1/fines/pending-actions
/general/v1/sos/ambulance
/general/v1/sos/dp
/internal/gateway/api/services
/internal/gateway/api/services/dashboard-api/dashboard
/internal/gateway/api/services/dubai-transaction/v1
/internal/gateway/api/services/external-integration/v1
/internal/gateway/api/services/general/v1
/internal/gateway/api/services/user-personalization/v1/unifyapps
/islam/v2/prayer/time
/maskanilandgrantmapservices/1.0.0/mapComponent
/maskaniservices/1.0.0/confirmreserveparcel
/mdubai/5.0.0/userdata
/mpaysubscription/5.0.0/addpaymentaccount
/mpaysubscription/5.0.0/allsubscriptionaccounts
/mpaysubscription/5.0.0/customerpaymentoptions
/mpaysubscription/5.0.0/deleteaccount
/mpaysubscription/5.0.0/entityserviceaccounts/v2
/mpaysubscription/5.0.0/lookup/v2
/mpaysubscription/5.0.0/profile/syncfromuaepassaccount
/mpaysubscription/5.0.0/register/fromuaepassaccount
/mpaysubscription/5.0.0/subscriptionaccount
/mydocument/api/v1/documents
/mydocument/api/v1/documents/family
/my-family/v1/members
/my-family/v1/members/pending-action
/my-property/v1/property
/my-property/v1/property/pending-action
/paperless-middleware/api/services
/rta/v1/abra-fines/fines/query
/rta/v1/abra-fines/payment-receipt
/rta/v1/parking-zones
/rta/v1/vehicles
/rta/v1/vehicles/pending-actions
/secure/dsg/googleapis
/secure/dxbnw/internal/uaepassauthentication/1.0.0/auth/oauth2
/secure/google/maps/1.0.0/api
/secure/rta/smartservices/1.0.0
/secure/sdg/dxbnw/configservice/1.0.0/api/services
/secure/sdg/dxbnw/internal/dp/1.0.0/api
/secure/sdg/dxbnw/internal/gdrfa/1.0.0/api
/secure/sdg/dxbnw/internal/rta/1.0.0/api
/secure/sdg/dxbnw/internal/userpersonalization/1.0.0/api
/services/cms/items
/services/user-personalization/user/personalization
/trustedx-resources/esignsp/v2/signer_processes
/uaepass/document-sign/token
/user-personalization/v1/delegation/token
/user-profile/api/v1/users/device
/user-profile/api/v1/users/v1/preferences
```

---

## 5. Hardcoded data inside bundled config assets (shared by both platforms)

`assets/flutter_assets/assets/`:

| File | Notes |
| --- | --- |
| `new_app_config.json` / `new_app_config_qa.json` | ~500 KB of pre-seeded announcements, service IDs, feature/config data (prod + QA) |
| `services_cards_data.json` | 162 service definitions (titles, descriptions EN/AR, fields, images) |
| `local_screen.json` | Hardcoded SOS test screen — includes **`971503971603`** as the mobile number and `971503971603` confirmation |
| `local_screen_v2.json` | Hardcoded test Email **`iphone.15@yopmail.com`** |
| `hm_configs.json` | Happiness Meter service-ID mapping (serviceId → hmServiceId, `gessEnabled`) |
| `faqs_configs.json` | FAQ content; contains support phone `600 560 000` and email `help@digitaldubai.ae` |
| `ddloadingindicator.json` | Lottie animation (not sensitive) |
| `wellknown/assetlinks.json` | Android App Links / signing fingerprint (see §2) |
| `wellknown/apple-app-site-association` | iOS App Links (Team IDs `PTEE8T35KX` / `X95CWGK9TY`) |

### 5.1 Full internal API endpoint map (baked into `new_app_config*.json`)

The bundled config is a complete offline snapshot of the backend CMS and includes
**194 production** and **232 QA** `base_url` + `end_point` pairs (per-service),
e.g.:

```
https://apis.dubai.gov.ae/secure/sdg/dxbnw/ddws/rta/1.0.0/api/services/ext/rta/vehicle/renew        # RenewVehicle
https://apis.dubai.gov.ae/secure/sdg/dxbnw/ddws/dp/1.0.0/api/services/ext/dp/sos                    # SOS
https://apis.dubai.gov.ae/secure/sdg/dxbnw/ddws/mbrhe/1.0.0/api/services/ext/mbrhe/landgrant        # LandGrant
https://api.dubai.gov.ae/secure/sdg/dubainow/paperless/5.0.0/api/entity/salik/manageprofile         # Salik
https://stg-apis.dubai.gov.ae/secure/sdg/dxbnw/mw-services/1.0.0/api/services/ext/bills?entity=DEWA&serviceCode=DEWABILL  # Bills (QA)
```

The full list is saved to **`dubainow/HARDCODED_ENDPOINTS.txt`** (434 lines).

### 5.2 Feature flags and catalog sizes (local defaults)

- `new_app_config.json`: **184 services**, **195 journeys**, **46 entities**, **33 feature flags**, **12 categories**, **38 sub-categories**; 179 unique service codes.
- Feature flags include `app_security_gate_enabled=true`, `tabby_enabled=true`, `enable_face_verification=true` (per-service), `happiness_meter_trigger_count=10`, `delay_in_seconds=10`, `pending_action_call=true`, `city_eye_floating_button_visibility=false`, `new_dubai_ai_flow=false`.
- `app_version` lists the full rollout history (`14.2.0` … `14.4.8`); `mobile_config.data_last_update = 2025-10-09T23:58:00.000Z`.
- Auth modes: `SOP1`, `SOP2`, `SOP3`, `GUEST`; social statuses `POD`, `RETIRED`, `SENIOR_CITIZEN`.
- `hm_configs.json`: 250 Happiness-Meter service mappings.

---

## 6. iOS bundle identifiers and extensions

| Executable | Bundle ID |
| --- | --- |
| Main app | `com.deg.mdubai` |
| PrayerTimesExtension (WidgetKit) | `com.deg.mdubai.prayertimes` — min iOS 18.1 |
| liveparkingExtension (WidgetKit / Live Activities) | `com.deg.mdubai.liveparking` — min iOS 18.1 |
| favoritesExtension (WidgetKit) | `com.deg.mdubai.favorites` — min iOS 18.6 |
| MyHubExtension (WidgetKit) | `com.deg.mdubai.userhub` — min iOS 18.6 |

Android widgets/broadcast receivers are declared under `com.deg.mdubai.qa.*` (a QA namespace leaked into the production manifest): `PrayerTimeSmall/LargeWidgetBroadCastReceiver`, `FavouriteWidgetBroadcastReceiverSmall/Large`, `MyHubLarge/SmallWidgetBroadcastReceiver`, `FavouriteWidgetConfigureActivity`.

---

## 7. Permissions (Android)

`INTERNET`, `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`, `ACCESS_NETWORK_STATE`, `SCHEDULE_EXACT_ALARM`, `USE_BIOMETRIC`, `CAMERA`, `READ_MEDIA_VISUAL_USER_SELECTED`, `READ_CONTACTS`, `WRITE_CONTACTS`, `POST_NOTIFICATIONS`, `VIBRATE`, `ACCESS_NOTIFICATION_POLICY`, `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`, `READ_MEDIA_AUDIO`, `WRITE_EXTERNAL_STORAGE` (maxSdk 28), `READ_EXTERNAL_STORAGE` (maxSdk 32), `RECEIVE_BOOT_COMPLETED`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, `WAKE_LOCK`, `FOREGROUND_SERVICE`, `com.google.android.c2dm.permission.RECEIVE`, `com.google.android.finsky.permission.BIND_GET_INSTALL_REFERRER_SERVICE`, `com.android.vending.CHECK_LICENSE`.

iOS usage strings: camera, photo library, microphone, speech recognition, contacts, calendars, Apple Music, Face ID, location, documents folder; background modes `fetch` + `remote-notification`; Live Activities enabled.

---

## 8. Third-party SDKs / frameworks

**Android native libs:** `libapp.so` (Flutter AOT), `libflutter.so`, `libpairipcore.so`, `libsigner.so`, `libsentry.so`, `libsentry-android.so`, `librive_native.so`, `libdartjni.so`, `libimage_processing_util_jni.so`, `libdatastore_shared_counter.so`, `libsurface_util_jni.so`, `libandroidx.graphics.path.so`.

**iOS frameworks:** Adjust / AdjustSig, AmplitudeCore / AmplitudeSwift, Firebase (Core, Installations, Messaging, AnalyticsConnector, GoogleDataTransport), GoogleUtilities, Google Maps resources, Sentry, SwiftyGif, SDWebImage, DKImagePickerController / DKPhotoGallery, TOCropViewController, SwiftProtobuf, plus Flutter plugins (uae pass, syncfusion PDF viewer, flutter_inappwebview, flutter_downloader, live_activities, rive_native, just_audio, speech_to_text, camera, geolocator, etc.).

**Notable Flutter packages** (from `package:` symbols in `libapp.so`): `dubai_now` (app), `sentry_flutter`, `adjust_sdk`, `amplitude_flutter`, `firebase_core/messaging/analytics`, `uaepass`, `graphql`/`gql`, `dio`, `go_router`, `riverpod`, `hive_ce`, `flutter_secure_storage`, `syncfusion_flutter_*`, `flutter_inappwebview`, `flutter_downloader`, `map_launcher`, `live_activities`, `pay`/`pay_platform_interface`, etc.

**Dependency bill of materials** (exact versions):

- Android: **`dubainow/ANDROID_DEPENDENCIES.txt`** (138 entries — AndroidX, Firebase, Play Services, Gradle/AGP `8.13.0`).
- iOS: **`dubainow/IOS_FRAMEWORKS.txt`** (77 frameworks — e.g. `AdjustSdk 5.8.0`, `AmplitudeSwift 1.17.5`, `FirebaseCore 12.6.0`, `Sentry 8.58.4`, `SDWebImage 5.21.7`, `SwiftProtobuf 1.38.1`).

---

## 9. Encryption / obfuscation deep-dive

Two distinct protections were found. Neither is a password/key-based cipher that can be "decrypted" offline.

### 9.1 Android — Google Play PairIP (VM virtualization)

- App entry point is `com.pairip.application.Application`; `libpairipcore.so` (ARM 32-bit, stripped) provides `VMRunner.executeVM(byte[] code, Object[] args)`.
- 27 assets in `assets/` (16-char hash names, e.g. `0CVezGtJEyr4W0Fu`) use magic `00 49 41 50` (`\0IAP`, version `2`). They are **PairIP virtual-machine programs**, not AES/data files.
- `VMRunner` reads `assets/<program>`, `com.pairip.VmDecryptor.decrypt()` is a **no-op** (the bytecode is interpreted by native code, not decrypted in Java), and calls `executeVM`.
- Native library methods (`BroadcastReceiver.onReceive`, `ListenableWorker.doWork`, `Glance` receivers, Adjust/Media3/Firebase receivers, `StartupLauncher`, …) had their bodies replaced with `VMRunner.invoke("<program>", args)`. Example map:

  | Program file | Replaced class |
  | --- | --- |
  | `0Css7BDXHxWItSJX` | `com.pairip.StartupLauncher` (launched from `MyApp.<clinit>`) |
  | `0CVezGtJEyr4W0Fu` | `androidx.glance.appwidget.MyPackageReplacedReceiver` |
  | `aFJWULoTHWvstgJy` | `com.adjust.sdk.AdjustReferrerReceiver` |
  | `iZKxETQ2ntYajVhS` | `com.google.android.gms.measurement.AppMeasurementReceiver` |
  | `rUIngrau4kqtaoli` | `io.flutter.plugins.urllauncher.WebViewActivity` |
  | `dBINO7lTTXUKbp7N` | `es.antonborri.home_widget.HomeWidgetBackgroundReceiver` |

- **What was recovered:** the programs are not string-encrypted — plaintext Java descriptors, class names and PairIP method names are embedded, e.g. `Lcom/deg/mdubai/qa/glance/FavouriteWidgetConfigureActivity$c2020060317;`, `Landroid/content/Intent;`, `/proc/self/cmdline`, `onCreate$001`, `getExtras$002`, `getIntent$003`, `getInt$004`, `setResult$005`, `finish$006`, `putExtra$007`, `setResult$008`, `finish$009`, `appWidgetId`, `invalid appWidgetId`.
- **Why full recovery is a VM RE task:** the rest of each file is custom VM bytecode. Deobfuscating it requires disassembling/reimplementing `libpairipcore.so`'s interpreter (no ARM disassembler was available in this environment; `objdump` lacks ARM support). The payoff is limited — only standard library method bodies are virtualized; the app's own logic lives in the (readable) Flutter `libapp.so`.
- PairIP additionally embeds the two signing-cert hashes listed in §2 and `SignatureCheck.verifyIntegrity()`.

### 9.2 iOS — Apple FairPlay DRM

- `LC_ENCRYPTION_INFO_64` reports `cryptid = 1` for `DubaiNow` (encrypted range `fileoff 16384`, size `10043392`), `App.framework/App` (`size 41533440`) and every framework/appex.
- `SC_Info/` contains the FairPlay metadata (`DubaiNow.sinf`, `.supp`, `.supf`, `.v4.supp`, `.v5.supf`, `.supx`, `Manifest.plist`); `sinf` contains `frma=game`, `schm=itun`.
- FairPlay uses a device-bound key. **It cannot be decrypted offline** — decryption requires a jailbroken/rooted device with the app installed and a runtime dumper (`bagbak`, `frida-ios-dump`, `Clutch`), or the vendor's keys. This is a hard blocker, not a missed step.
- Everything not DRM-protected in the IPA (all plists, entitlements, `flutter_assets`, localization, `Assets.car`) was extracted; no encrypted app assets were found besides FairPlay.

### 9.3 App-level crypto inventory

- The Dart code imports `pointycastle` and uses AES classes (`AesCipher`, `AES_GCM_NoPadding`, `CBCBlockCipherMac`, …) for PDF/`syncfusion` document handling and general crypto — **no hardcoded AES key/IV for app data was found**.
- `flutter_secure_storage` delegates to Android Keystore / iOS Keychain (`KeychainAccessibility`, `flutter_secure_storage_service`); no embedded storage key exists.
- `Hive`/`hive_ce`/`sqflite` caches are used but no Hive AES key literal was found.
- `NOTICES.Z` is a standard Flutter license bundle (gzip of 1.8 MB of package licenses, not encrypted).
- `new_app_config.json` / `new_app_config_qa.json` are **plaintext** offline copies of the backend CMS (services, journeys, endpoints, feature flags) — they are the richest source of hardcoded information and required no decryption (see §5).
- No password-protected ZIP entries, keystores (`.jks`/`.keystore`), `.p12`/`.pem`/`.crt` files or PGP blobs were present in either package.
- `SC_Info/Manifest.plist` confirms every iOS framework (`AdjustSdk`, `Amplitude*`, `Firebase*`, `Sentry`, `Flutter`, `App`, all `.appex`es) is individually FairPlay-encrypted.

---

## 10. Notes / caveats

- iOS native code could **not** be string-dumped because Apple FairPlay encryption (`cryptid=1`) covers `__TEXT` of `DubaiNow`, `App.framework/App` and every framework/appex. All values above from iOS come from unencrypted property lists, entitlements and the shared Flutter asset bundle.
- PairIP (Android) is VM virtualization, not encryption; embedded plaintext identifiers were recovered, but full method recovery needs VM reverse-engineering.
- App-specific Adjust app token and Amplitude API key were not found as literals; they appear to be supplied at runtime. The Happiness Meter client ID/secret also remain unresolved, but a strong UAE Pass `clientID` candidate (`dubainow_mobileapp_prod_v2`) and its scopes were recovered.
- The Google Maps iOS API key is set in Swift code inside the encrypted `DubaiNow` binary and was not recoverable; the Android Maps key is listed in §2.
- Native Android hardcoded secret **was** recovered from `classes7.dex` (see §2): the prayer-times `X-API-Key`, plus the real APK signing certificate.
- The iOS build ships a few assets the Android build does not (`banner_food_for_all.png`, extra RTA parking-test SVGs, `range_rover.svg`, `ic_parking*`, `pcfc_my_marine_license.svg`), indicating the iOS build is slightly ahead/divergent.
</content>
