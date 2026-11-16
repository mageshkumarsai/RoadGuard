# RoadGuard – Completion Checklist

Status key: **COMPLETED** (verified by a passing test run on your machine) · **TESTING REQUIRED** (code written, not yet verified) · **NEEDS CORRECTION** · **NOT IMPLEMENTED**

> Nothing is marked COMPLETED yet. The code was written in an environment without Django, so no test could be run there. Items move to COMPLETED only after you run the commands in `docs/RUN_AND_VERIFY.md` and send the results.

## Authentication
| Item | Status | Where |
|---|---|---|
| Customer login page | TESTING REQUIRED | `roadside/views.py` `_login_view`, `registration/login.html` |
| Provider login page | TESTING REQUIRED | same |
| Role-based login and redirect | TESTING REQUIRED | `dashboard` view |
| Customers blocked from provider pages | TESTING REQUIRED | `provider_required` |
| Providers blocked from customer pages | TESTING REQUIRED | `customer_required` |
| Login / validation messages (red alerts) | TESTING REQUIRED | `MESSAGE_TAGS` in settings |
| Customer & provider registration | TESTING REQUIRED | `RegistrationForm`, `register` |

## Provider side
| Item | Status |
|---|---|
| Dashboard: open requests list | TESTING REQUIRED (was broken: wrong template variable names) |
| Dashboard: assigned requests list | TESTING REQUIRED (same bug) |
| Customer/request info & location on dashboard | TESTING REQUIRED |
| Provider map with nearby open requests, popups | TESTING REQUIRED (was broken: missing `provider_data`) |
| 10 km filtering with haversine + GPS validation | TESTING REQUIRED |
| Accept (atomic, one winner, distance re-checked) | TESTING REQUIRED |
| Reject | TESTING REQUIRED (new, was missing) |
| Request detail preview before accepting | TESTING REQUIRED (new) |
| Status workflow ACCEPTED → IN_PROGRESS → RESOLVED only | TESTING REQUIRED (new) |
| Progress note visible to customer | TESTING REQUIRED (new) |

## Customer side
| Item | Status |
|---|---|
| Create request with GPS (browser button + map click) | TESTING REQUIRED |
| GPS and district/city validation | TESTING REQUIRED |
| Request progress tracker | TESTING REQUIRED |
| Assigned provider details | TESTING REQUIRED |
| Completed service details / timeline | TESTING REQUIRED |
| Cancel request (while Open/Accepted) | TESTING REQUIRED (new) |
| PDF receipt (escaped text, timeline section) | TESTING REQUIRED |

## PWA and mobile application
| Item | Status | Where |
|---|---|---|
| Web app manifest, standalone display, root scope and home start URL | TESTING REQUIRED | `templates/manifest.webmanifest` |
| 192px, 512px, maskable and Apple touch icons | TESTING REQUIRED | `static/icons/` |
| Root-scoped service worker and cache versioning | TESTING REQUIRED | `templates/service-worker.js`, `roadside/views.py` |
| Offline fallback without caching personal HTML/data/PDFs | TESTING REQUIRED | `templates/service-worker.js`, `templates/offline.html` |
| Android native install prompt when browser supports it | TESTING REQUIRED | `static/js/app.js`, `templates/base.html` |
| iPhone/iPad Safari Add to Home Screen instructions | TESTING REQUIRED | `static/js/app.js`, `templates/base.html` |
| Apple mobile web app metadata and safe-area viewport | TESTING REQUIRED | `templates/base.html` |
| Responsive navigation, cards, forms, maps and touch targets | TESTING REQUIRED | `static/css/style.css` and page templates |
| Real Android installation and launch | TESTING REQUIRED (device test) | HTTPS deployment required |
| Real iPhone/iPad installation and launch | TESTING REQUIRED (device test) | HTTPS deployment + Safari required |
| Mobile GPS and Leaflet map operation | TESTING REQUIRED (device test) | HTTPS + location permission required |

## UI
| Item | Status |
|---|---|
| Customer dashboard redesign | TESTING REQUIRED |
| Provider dashboard redesign | TESTING REQUIRED |
| Bootstrap Icons loaded (icons were missing before) | TESTING REQUIRED |
| Mobile responsiveness (manual check in browser dev tools) | TESTING REQUIRED |
| Screenshots for the report | NOT IMPLEMENTED (you must capture them – see demo script) |

## Quality
| Item | Status |
|---|---|
| `manage.py check` | TESTING REQUIRED |
| `makemigrations --check` | TESTING REQUIRED |
| `migrate` on your existing database | TESTING REQUIRED |
| `manage.py test` (≈120 tests) | TESTING REQUIRED |
| requirements.txt | TESTING REQUIRED |
| Documentation + demo script | COMPLETED (written; screenshots/test results sections to be filled by you) |
