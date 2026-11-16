# RoadGuard mobile app and PWA guide

RoadGuard is a Django website enhanced as a Progressive Web App (PWA). It is not a separately packaged native Android APK or iOS App Store application. A PWA can be installed from a supported mobile browser and launched from the device home screen.

## What is included

- Web app manifest with RoadGuard name, standalone display, home-page start URL and app icons.
- Android install control that uses the browser's native `beforeinstallprompt` event when the browser offers it.
- iPhone/iPad instructions for Safari's Share → Add to Home Screen flow.
- Apple web-app metadata and viewport safe-area support.
- Responsive navigation, cards, forms, map containers and touch targets.
- Root-scoped service worker.
- Offline fallback page. The worker caches only public app-shell files; it does not cache HTML pages, authenticated data, assistance requests, map data or PDF receipts.

## Requirements before real-phone installation

1. Deploy RoadGuard to a web host with a valid HTTPS certificate. Service workers and browser geolocation require a secure context. `localhost` is treated as secure only on the same device running the development server.
2. Set `DEBUG=False`, configure a strong `DJANGO_SECRET_KEY`, and set `ALLOWED_HOSTS` to the deployed domain.
3. Run `python manage.py collectstatic` as part of deployment and configure the web server to serve `STATIC_ROOT` files.
4. Confirm that `/manifest.json`, `/service-worker.js`, `/offline/`, and every `/static/icons/...` URL return successfully over HTTPS.
5. Open the site once while online so the browser can register and install the service worker.

A phone's `http://127.0.0.1:8000/` address points to the phone itself, not the Windows computer. Using the computer's private LAN IP over plain HTTP is not sufficient for normal PWA installation or geolocation on a phone. Use HTTPS hosting or a secure HTTPS tunnel for device testing.

## Install on Android

1. Open the deployed HTTPS RoadGuard URL in Chrome (or another browser that supports PWA installation).
2. Sign in or browse to the home page.
3. Tap **Install app** in the RoadGuard navigation when the browser provides its install prompt.
4. If no native prompt appears, open the browser's three-dot menu and choose **Install app** or **Add to Home screen** (the wording varies by browser/version).
5. Launch RoadGuard from the new home-screen icon.

## Install on iPhone or iPad

1. Open the deployed HTTPS RoadGuard URL in **Safari**. Other iOS browsers may not expose the same Add to Home Screen flow.
2. Tap the **Share** icon.
3. Scroll and choose **Add to Home Screen**.
4. Confirm the RoadGuard name and tap **Add**.
5. Launch RoadGuard from the home-screen icon.

The iOS flow is manual; iOS does not use the Chromium `beforeinstallprompt` event. The RoadGuard Install app control displays these instructions on iOS.

## Test checklist

- [ ] Manifest opens as valid JSON and all icon URLs return HTTP 200.
- [ ] Service worker returns JavaScript with `Service-Worker-Allowed: /` and controls pages after reload.
- [ ] Android browser offers installation and the installed app opens in standalone mode.
- [ ] iOS Safari Add to Home Screen creates the RoadGuard icon and opens the site in its web-app presentation.
- [ ] Navigation menu, forms, dashboard cards, request details and map fit phone widths without page-level horizontal scrolling.
- [ ] GPS permission can be granted and current location is captured on HTTPS.
- [ ] Leaflet map is usable by touch and markers/popups remain readable.
- [ ] While offline, navigation displays only the safe offline page; reconnecting restores normal pages.
- [ ] Customer/provider login, request creation, acceptance, status updates and receipt downloads still require an internet connection and continue to work online.

## Known limitations

- This PWA is not an APK, IPA, Play Store or App Store release. Native packaging and store publication would be a separate project.
- Live maps require internet access and external map tiles. Offline mode does not provide live assistance, GPS updates or map tiles.
- Background location tracking, push notifications and native emergency calling are not implemented.
- Browser support and installation labels vary by operating system and browser version. Verify on actual Android and iOS devices before claiming device testing is complete.
