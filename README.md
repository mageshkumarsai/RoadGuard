# RoadGuard – Roadside Assistance Platform (Django)

Connects vehicle owners (customers) with nearby mechanics and towing providers in Tamil Nadu using GPS, Leaflet maps and a 10 km matching radius.

## Features
- Customer and provider registration, role-based login and dashboards
- Tamil Nadu district/city selection, GPS capture, Leaflet map
- Providers see only open requests within 10 km (haversine distance) that match their service type
- Accept (one provider wins, enforced by a transaction + row lock + conditional update), reject, status workflow
- Customer tracking, assigned-provider details, cancel, PDF receipt
- Installable PWA (manifest, Android install prompt, iPhone Add to Home Screen guidance, app icons and privacy-safe offline fallback)
- Responsive mobile layouts, touch-friendly controls and safe-area support

## Setup (Windows)
```powershell
py -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000/

## Tests
```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test -v 2
```

## Request status workflow
`OPEN → ACCEPTED → IN_PROGRESS → RESOLVED`. A customer may cancel while OPEN or ACCEPTED. No other transitions are allowed.

## Notes and limits
- Maps need internet (Leaflet and OpenStreetMap tiles load from CDNs).
- Geolocation and service workers require a secure context: HTTPS in deployment, or `localhost`/`127.0.0.1` on the development computer.
- On Android, supported Chrome/Edge browsers can show the native install prompt. On iPhone/iPad, users install from Safari using Share → Add to Home Screen.
- A phone cannot use the development computer’s `127.0.0.1` address. For real-device testing, deploy to an HTTPS host or use a properly configured HTTPS development tunnel.
- Only public static assets and the offline fallback are cached. HTML pages, account data, request details, map data and PDF receipts are not cached.
- Demonstration project: no payments, live tracking or push notifications.
- For deployment set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, and update `ALLOWED_HOSTS`.

See `docs/` for the full documentation, checklist, demo script and `MOBILE_PWA_GUIDE.md`.
