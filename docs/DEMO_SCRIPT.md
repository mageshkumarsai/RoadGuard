# RoadGuard – Demonstration Script (about 8 minutes)

**Preparation:** run `python manage.py migrate` and `python manage.py runserver`. Use two browser profiles (or one normal and one private window) so you can stay logged in as customer and provider at the same time. Allow location access for `127.0.0.1`.

1. **Introduce** (30 s): "RoadGuard connects stranded drivers with nearby mechanics and towing providers within 10 km."
2. **Provider registration** (1 min): Window A → Create account → Service provider → fill business name, type "Mechanic and towing", phone. Open *My provider profile*, click *Use My Current Location*, keep *Available* ticked, Save.
3. **Second provider** (optional, 30 s): register a second provider with the same steps to show only one can accept.
4. **Customer registration** (1 min): Window B → Create account → Vehicle owner.
5. **Create request** (1 min): *Request assistance* → fill vehicle, issue, phone, district/city → click *Use My Current Location* (or click the map) → Submit. Show the progress tracker: "Waiting for a Provider".
6. **Provider sees the request** (1 min): Window A → Provider dashboard. Point out the distance badge, the map marker and its popup, and the "within 10 km" counter. Open *View details*.
7. **Accept and duplicate prevention** (1 min): Provider 1 clicks *Accept*. Switch to Provider 2 and refresh: the request is gone; if you press Accept from an old tab, it says it was already accepted.
8. **Customer sees the provider** (30 s): Window B refresh → "Provider Assigned" with business name and phone.
9. **Work progress** (1 min): Provider opens the job → *Start service* (add a note, e.g. "On site") → customer refreshes and sees *In progress* and the note → provider clicks *Mark as completed*.
10. **Completion and receipt** (1 min): Customer sees "Assistance Completed" with the timeline → *Download Receipt PDF* → open the PDF.
11. **Extra checks** (1 min): try opening the provider dashboard URL while logged in as customer (access denied); show a provider rejecting a request; show the PWA install icon in the browser address bar and the mobile layout using browser dev tools (device toolbar).
12. **Mobile/PWA demonstration** (1 min): open the HTTPS deployment on Android Chrome and use **Install app** or the browser's install menu. On iPhone, open the same URL in Safari → Share → Add to Home Screen. Launch from the new icon and show the responsive customer/provider pages. Test GPS permission and the Leaflet map on the device. This step requires a real HTTPS deployment; a desktop `127.0.0.1` server is not a phone-accessible production URL.
13. **Close** (30 s): mention the test suite (`python manage.py test`), the PWA's offline-safe shell, and future enhancements.

**If something goes wrong:** no map tiles → check internet; location blocked → click the map instead; no open requests for the provider → confirm provider has GPS saved and is Available, and that the request is within 10 km of the provider.
