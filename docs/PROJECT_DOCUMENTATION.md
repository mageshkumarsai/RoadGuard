# RoadGuard – Roadside Assistance Platform
Project documentation

## 1. Introduction
RoadGuard is a web application built with Python and Django that helps drivers who break down on the road find a nearby mechanic or towing provider. Customers describe the problem and share their GPS location; providers within 10 km see the request and one of them accepts it. The customer tracks progress and downloads a PDF receipt.

## 2. Problem statement
When a vehicle breaks down, drivers usually phone around, cannot describe their exact location, and do not know which provider is close or available. Providers, in turn, have no structured way to see who needs help nearby.

## 3. Objectives
- Let customers raise a request with an exact GPS location.
- Show each request only to suitable providers within 10 km.
- Guarantee that exactly one provider can accept a request.
- Give both sides clear, accurate progress tracking.
- Produce a PDF receipt for completed assistance.

## 4. Existing system
Phone calls, word of mouth and generic listing sites: no location sharing, no availability information, no request tracking, no records.

## 5. Proposed system
A role-based web portal with GPS-aware matching, safe assignment, a fixed status workflow, and an installable PWA front-end.

## 6. Technologies used
Python 3, Django 5.2, SQLite, ReportLab (PDF), Bootstrap 5.3, Bootstrap Icons, Leaflet 1.9 with OpenStreetMap tiles, browser Geolocation API, service worker and web manifest (PWA).

## 7. System requirements
Python 3.10+, a modern browser (Chrome/Edge recommended), internet access for CDN assets and map tiles, about 100 MB disk.

## 8. Main features
Customer: register, create a request (district/city, GPS, map click), track status, see provider details, cancel, download receipt.
Provider: profile with GPS location and availability, nearby open requests with distance, request preview, accept or reject, update status with a progress note, nearby-request map.
System: role-based access control, atomic assignment, validated GPS, escaped PDF text, PWA.

## 9. System architecture
Browser (HTML/Bootstrap/Leaflet/JS) → Django URL router → views (role decorators, workflow logic) → models/ORM → SQLite. Helper module `roadside/utils.py` contains the haversine distance and the nearby-request query. ReportLab generates PDFs in memory. A service worker served at `/service-worker.js` provides offline fallback only; HTML pages are never cached.

Files: `config/` (settings, urls), `roadside/` (models, forms, views, urls, utils, tests, migrations), `templates/`, `static/` (css, js, icons).

## 10. Database structure
- **User** (Django auth): username, email, names, password.
- **Provider**: user (1-to-1), business_name, service_type, phone, description, address, latitude, longitude, is_available.
- **AssistanceRequest**: customer (FK User), provider (FK Provider, nullable), service_needed, vehicle, issue_description, phone, state, district, city, location_text, latitude, longitude, status, progress_note, accepted_at, started_at, completed_at, created_at, updated_at.
- **RequestRejection**: request (FK), provider (FK), created_at; unique per (request, provider).

A user is a provider if a Provider row exists for them; otherwise a customer.

## 11. Customer workflow
Register → log in (Customer login) → Request assistance (details + GPS) → request becomes Open → provider accepts (customer sees provider name/phone) → provider starts and completes → customer views completed details → downloads PDF receipt.

## 12. Service provider workflow
Register as provider → log in (Provider login) → add GPS location in profile → view open requests within 10 km (list and map) → preview, accept or reject → Start service → Mark as completed (optional progress note).

## 13. Status workflow
OPEN → ACCEPTED (provider accepts) → IN_PROGRESS (provider) → RESOLVED (provider). Customer may CANCEL while OPEN or ACCEPTED. All other changes are refused by the server.

## 14. Nearby filtering and safe assignment
Distance is the haversine great-circle distance between provider and request coordinates. A request is eligible if it is OPEN, unassigned, within 10 km, matches the service type, and has not been rejected by that provider. Missing or out-of-range coordinates are skipped. When a provider accepts, the server repeats every check inside `transaction.atomic()` with `select_for_update()` and performs a conditional `UPDATE ... WHERE status='OPEN' AND provider IS NULL`; only one provider's update can change a row.

## 15. Screenshots
Insert your own screenshots here after running the project: home page; registration; customer dashboard; create request with map; provider dashboard with map; request detail (open, accepted, completed); PDF receipt; PWA install prompt; mobile view.

## 16. Testing results
Automated suite: `python manage.py test -v 2` (≈120 tests covering registration, login, role access, request creation, GPS validation, distance and 10 km filtering, accept/duplicate-accept, reject, status workflow, cancel, PDF, PWA, end-to-end flow).
Paste your results here: `Ran __ tests in __s — OK`.

## 17. Mobile application / PWA
RoadGuard is delivered as a responsive Progressive Web App rather than a separately packaged native APK or IPA. On supported Android browsers, the navigation's **Install app** control can invoke the browser's native installation prompt. On iPhone/iPad, the same control explains Safari's Share → Add to Home Screen process. The manifest sets standalone display mode and provides standard, maskable and Apple touch icons.

The root-scoped service worker caches only public static application-shell assets and a generic offline page. It deliberately does not cache HTML pages, authenticated customer/provider information, assistance requests, map data or PDF receipts. Live requests, GPS-based matching and map tiles require an internet connection. Browser geolocation and service-worker installation require HTTPS in deployment (localhost is permitted for same-device development).

Real Android and iPhone installation, mobile GPS and map interaction must be checked on physical devices after deploying to HTTPS. Follow `docs/MOBILE_PWA_GUIDE.md`; do not mark those device checks complete based only on automated tests.

## 18. Conclusion and future enhancements
RoadGuard demonstrates a complete request-to-receipt workflow with location-aware matching and safe assignment. Possible enhancements: live provider tracking, SMS/push notifications, payments and pricing, provider ratings, PostgreSQL for production, automatic geocoding of addresses, multi-state support, and an admin analytics dashboard.
