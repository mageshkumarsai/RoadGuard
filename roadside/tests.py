"""RoadGuard automated tests.

Run with:  python manage.py test -v 2
"""
import json
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import AssistanceRequest, Provider, RequestRejection
from .utils import (
    calculate_distance,
    is_valid_coordinate,
    nearby_open_requests,
    to_float,
)

PASSWORD = "Str0ng-Pass!word42"

# Provider base location (Ranipet area). 0.01 degree of latitude is ~1.11 km.
BASE_LAT = Decimal("12.924900")
BASE_LNG = Decimal("79.333000")


def offset(lat_km):
    """Latitude that is roughly lat_km north of the base point."""
    return (BASE_LAT + Decimal(str(lat_km / 111.19))).quantize(Decimal("0.000001"))


def make_customer(username="customer1", email=None):
    return User.objects.create_user(
        username=username,
        password=PASSWORD,
        email=email or f"{username}@example.com",
        first_name="Cus",
    )


def make_provider(
    username="provider1",
    service_type="BOTH",
    lat=BASE_LAT,
    lng=BASE_LNG,
    available=True,
):
    user = User.objects.create_user(
        username=username, password=PASSWORD, email=f"{username}@example.com"
    )
    return Provider.objects.create(
        user=user,
        business_name=f"{username} garage",
        service_type=service_type,
        phone="9000000000",
        latitude=lat,
        longitude=lng,
        is_available=available,
    )


def make_request(customer, lat_km=3, service="EITHER", **extra):
    defaults = dict(
        customer=customer,
        service_needed=service,
        vehicle="Swift Dzire",
        issue_description="Engine will not start",
        phone="9000000001",
        state="Tamil Nadu",
        district="Ranipet",
        city="Ranipet",
        location_text="Main road",
        latitude=offset(lat_km) if lat_km is not None else None,
        longitude=BASE_LNG if lat_km is not None else None,
    )
    defaults.update(extra)
    return AssistanceRequest.objects.create(**defaults)


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


# ---------------------------------------------------------------------------
# Original model tests (kept)
# ---------------------------------------------------------------------------

class RoadGuardModelTests(TestCase):
    def test_provider_creation(self):
        user = User.objects.create_user(username="mechanic", password="test-pass-123")
        provider = Provider.objects.create(
            user=user, business_name="Test Garage", service_type="MECHANIC", phone="9000000000"
        )
        self.assertEqual(str(provider), "Test Garage")

    def test_assistance_request_default_status(self):
        user = User.objects.create_user(username="customer", password="test-pass-123")
        item = AssistanceRequest.objects.create(
            customer=user, vehicle="Car", issue_description="Flat tyre", phone="9000000001"
        )
        self.assertEqual(item.status, "OPEN")


class MigrationTests(TestCase):
    def test_no_missing_migrations(self):
        out = StringIO()
        try:
            call_command("makemigrations", "--check", "--dry-run", stdout=out)
        except SystemExit:
            self.fail("Model changes are missing a migration:\n" + out.getvalue())


# ---------------------------------------------------------------------------
# Distance and GPS helpers
# ---------------------------------------------------------------------------

class DistanceTests(SimpleTestCase):
    def test_same_point_is_zero(self):
        self.assertAlmostEqual(calculate_distance(12.9, 79.3, 12.9, 79.3), 0.0, places=6)

    def test_one_degree_latitude_is_about_111_km(self):
        self.assertAlmostEqual(calculate_distance(10, 79, 11, 79), 111.19, delta=0.2)

    def test_chennai_to_bengaluru_known_distance(self):
        # Chennai (13.0827, 80.2707) -> Bengaluru (12.9716, 77.5946) is ~290 km.
        self.assertAlmostEqual(
            calculate_distance(13.0827, 80.2707, 12.9716, 77.5946), 290, delta=5
        )

    def test_distance_is_symmetric(self):
        a = calculate_distance(12.9, 79.3, 13.1, 80.2)
        b = calculate_distance(13.1, 80.2, 12.9, 79.3)
        self.assertAlmostEqual(a, b, places=9)

    def test_decimal_inputs_work(self):
        self.assertGreater(calculate_distance(Decimal("12.9"), Decimal("79.3"), Decimal("13.0"), Decimal("79.3")), 10)

    def test_valid_coordinates(self):
        self.assertTrue(is_valid_coordinate(12.9, 79.3))
        self.assertTrue(is_valid_coordinate("12.9", "79.3"))
        self.assertTrue(is_valid_coordinate(-90, 180))

    def test_invalid_coordinates(self):
        for lat, lng in [
            (None, 79), (12, None), (91, 79), (-91, 79), (12, 181), (12, -181),
            ("abc", 79), (float("nan"), 79), (float("inf"), 79), ("", ""),
        ]:
            with self.subTest(lat=lat, lng=lng):
                self.assertFalse(is_valid_coordinate(lat, lng))

    def test_to_float_handles_garbage(self):
        self.assertIsNone(to_float("x"))
        self.assertIsNone(to_float(None))
        self.assertEqual(to_float(Decimal("1.5")), 1.5)


class NearbyFilterTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.provider = make_provider()

    def ids(self, provider=None):
        return [r.pk for r in nearby_open_requests(provider or self.provider)]

    def test_request_inside_10km_is_listed_with_distance(self):
        req = make_request(self.customer, lat_km=5)
        results = nearby_open_requests(self.provider)
        self.assertEqual([r.pk for r in results], [req.pk])
        self.assertAlmostEqual(results[0].distance_km, 5.0, delta=0.2)

    def test_request_outside_10km_is_not_listed(self):
        make_request(self.customer, lat_km=12)
        self.assertEqual(self.ids(), [])

    def test_boundary_just_inside_and_just_outside(self):
        inside = make_request(self.customer, lat_km=9.8)
        make_request(self.customer, lat_km=10.3)
        self.assertEqual(self.ids(), [inside.pk])

    def test_results_sorted_nearest_first(self):
        far = make_request(self.customer, lat_km=8)
        near = make_request(self.customer, lat_km=1)
        mid = make_request(self.customer, lat_km=4)
        self.assertEqual(self.ids(), [near.pk, mid.pk, far.pk])

    def test_request_without_gps_is_skipped(self):
        make_request(self.customer, lat_km=None)
        self.assertEqual(self.ids(), [])

    def test_request_with_invalid_gps_is_skipped(self):
        make_request(self.customer, lat_km=3, latitude=Decimal("95.000000"))
        self.assertEqual(self.ids(), [])

    def test_provider_without_gps_sees_nothing(self):
        make_request(self.customer, lat_km=2)
        no_gps = make_provider("nogps", lat=None, lng=None)
        self.assertEqual(self.ids(no_gps), [])

    def test_unavailable_provider_sees_nothing(self):
        make_request(self.customer, lat_km=2)
        away = make_provider("away", available=False)
        self.assertEqual(self.ids(away), [])

    def test_only_open_unassigned_requests(self):
        make_request(self.customer, lat_km=2, status="ACCEPTED", provider=self.provider)
        make_request(self.customer, lat_km=2, status="RESOLVED")
        make_request(self.customer, lat_km=2, status="CANCELLED")
        self.assertEqual(self.ids(), [])

    def test_service_type_filtering(self):
        mech_only = make_provider("mech", service_type="MECHANIC")
        towing_req = make_request(self.customer, lat_km=2, service="TOWING")
        either_req = make_request(self.customer, lat_km=2, service="EITHER")
        self.assertEqual(self.ids(mech_only), [either_req.pk])
        self.assertCountEqual(self.ids(), [towing_req.pk, either_req.pk])  # BOTH provider

    def test_rejected_requests_are_hidden_from_that_provider_only(self):
        req = make_request(self.customer, lat_km=2)
        other = make_provider("other")
        RequestRejection.objects.create(request=req, provider=self.provider)
        self.assertEqual(self.ids(), [])
        self.assertEqual(self.ids(other), [req.pk])


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegistrationTests(TestCase):
    def data(self, **extra):
        base = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "new@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
            "role": "CUSTOMER",
        }
        base.update(extra)
        return base

    def test_register_page_loads(self):
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)

    def test_customer_registration_creates_user_without_provider(self):
        response = self.client.post(reverse("register"), self.data())
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        user = User.objects.get(username="newuser")
        self.assertFalse(Provider.objects.filter(user=user).exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_provider_registration_creates_provider_profile(self):
        response = self.client.post(
            reverse("register"),
            self.data(
                username="newprov", email="p@example.com", role="PROVIDER",
                business_name="Quick Fix", service_type="TOWING", phone="9876543210",
            ),
        )
        self.assertEqual(response.status_code, 302)
        provider = Provider.objects.get(user__username="newprov")
        self.assertEqual(provider.business_name, "Quick Fix")
        self.assertEqual(provider.service_type, "TOWING")

    def test_provider_registration_requires_business_fields(self):
        response = self.client.post(reverse("register"), self.data(role="PROVIDER"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(reverse("register"), self.data(password2="different-pass-9"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_duplicate_email_is_rejected(self):
        make_customer("existing", email="new@example.com")
        response = self.client.post(reverse("register"), self.data())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_invalid_phone_rejected_for_provider(self):
        response = self.client.post(
            reverse("register"),
            self.data(role="PROVIDER", business_name="X", service_type="MECHANIC", phone="abc"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())


# ---------------------------------------------------------------------------
# Login and role-based access
# ---------------------------------------------------------------------------

class LoginTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.provider = make_provider()

    def login(self, url_name, username):
        return self.client.post(
            reverse(url_name), {"username": username, "password": PASSWORD}
        )

    def test_login_pages_load(self):
        for name in ("login", "customer_login", "provider_login"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_customer_login_redirects_to_customer_dashboard(self):
        response = self.login("customer_login", "customer1")
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        follow = self.client.get(reverse("dashboard"))
        self.assertRedirects(follow, reverse("customer_dashboard"))

    def test_provider_login_redirects_to_provider_dashboard(self):
        response = self.login("provider_login", "provider1")
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        follow = self.client.get(reverse("dashboard"))
        self.assertRedirects(follow, reverse("provider_dashboard"))

    def test_provider_cannot_use_customer_login(self):
        response = self.login("customer_login", "provider1")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(any("Provider login" in m for m in message_texts(response)))

    def test_customer_cannot_use_provider_login(self):
        response = self.login("provider_login", "customer1")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(any("Customer login" in m for m in message_texts(response)))

    def test_wrong_password_shows_error(self):
        response = self.client.post(
            reverse("customer_login"), {"username": "customer1", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "Please enter a correct username and password")

    def test_unknown_user_rejected(self):
        response = self.login("provider_login", "ghost")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post_and_logs_out(self):
        self.client.force_login(self.customer)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_error_messages_use_bootstrap_danger_class(self):
        response = self.login("customer_login", "provider1")
        self.assertContains(response, "alert-danger")


class RoleAccessTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.provider = make_provider()
        self.req = make_request(self.customer)

    def test_anonymous_redirected_to_login(self):
        for name, args in [
            ("customer_dashboard", []), ("provider_dashboard", []), ("create_request", []),
            ("provider_profile", []), ("map", []), ("request_detail", [self.req.pk]),
            ("download_invoice", [self.req.pk]),
        ]:
            with self.subTest(page=name):
                response = self.client.get(reverse(name, args=args))
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response["Location"])

    def test_customer_blocked_from_provider_pages(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("provider_dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("provider_profile")).status_code, 403)
        for name in ("accept_request", "reject_request"):
            response = self.client.post(reverse(name, args=[self.req.pk]))
            self.assertEqual(response.status_code, 403, name)

    def test_provider_blocked_from_customer_pages(self):
        self.client.force_login(self.provider.user)
        self.assertEqual(self.client.get(reverse("customer_dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("create_request")).status_code, 403)

    def test_customer_cannot_change_status(self):
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("update_status", args=[self.req.pk]), {"status": "IN_PROGRESS"}
        )
        self.assertEqual(response.status_code, 403)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "OPEN")

    def test_post_only_endpoints_reject_get(self):
        self.client.force_login(self.provider.user)
        for name in ("accept_request", "reject_request", "update_status"):
            self.assertEqual(self.client.get(reverse(name, args=[self.req.pk])).status_code, 405, name)

    def test_dashboards_render_for_correct_role(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("customer_dashboard")).status_code, 200)
        self.client.force_login(self.provider.user)
        self.assertEqual(self.client.get(reverse("provider_dashboard")).status_code, 200)


# ---------------------------------------------------------------------------
# Request creation and GPS validation
# ---------------------------------------------------------------------------

class CreateRequestTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.client.force_login(self.customer)

    def data(self, **extra):
        base = {
            "service_needed": "EITHER",
            "vehicle": "Hyundai i20",
            "issue_description": "Flat tyre, no spare",
            "phone": "9876543210",
            "state": "Tamil Nadu",
            "district": "Ranipet",
            "city": "Walajah",
            "location_text": "Near bus stand",
            "latitude": "12.924900",
            "longitude": "79.333000",
        }
        base.update(extra)
        return base

    def test_form_page_loads(self):
        self.assertEqual(self.client.get(reverse("create_request")).status_code, 200)

    def test_valid_request_is_created_and_open(self):
        response = self.client.post(reverse("create_request"), self.data())
        item = AssistanceRequest.objects.get()
        self.assertRedirects(response, reverse("request_detail", args=[item.pk]))
        self.assertEqual(item.customer, self.customer)
        self.assertEqual(item.status, "OPEN")
        self.assertIsNone(item.provider)
        self.assertEqual(item.latitude, Decimal("12.924900"))

    def test_missing_gps_is_rejected(self):
        response = self.client.post(reverse("create_request"), self.data(latitude="", longitude=""))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AssistanceRequest.objects.count(), 0)
        self.assertContains(response, "select your breakdown location")

    def test_out_of_range_gps_is_rejected(self):
        for lat, lng in [("95.000000", "79.0"), ("12.0", "190.0"), ("-91", "10")]:
            with self.subTest(lat=lat, lng=lng):
                response = self.client.post(
                    reverse("create_request"), self.data(latitude=lat, longitude=lng)
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(AssistanceRequest.objects.count(), 0)

    def test_non_numeric_gps_is_rejected(self):
        response = self.client.post(reverse("create_request"), self.data(latitude="abc"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AssistanceRequest.objects.count(), 0)

    def test_city_must_belong_to_district(self):
        response = self.client.post(
            reverse("create_request"), self.data(district="Ranipet", city="Ooty")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AssistanceRequest.objects.count(), 0)

    def test_state_must_be_tamil_nadu(self):
        response = self.client.post(reverse("create_request"), self.data(state="Kerala"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AssistanceRequest.objects.count(), 0)

    def test_missing_required_fields_rejected(self):
        response = self.client.post(reverse("create_request"), self.data(vehicle="", phone=""))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AssistanceRequest.objects.count(), 0)


class ProviderProfileTests(TestCase):
    def setUp(self):
        self.provider = make_provider(lat=None, lng=None)
        self.client.force_login(self.provider.user)

    def data(self, **extra):
        base = {
            "business_name": "Updated Garage",
            "service_type": "BOTH",
            "phone": "9876543210",
            "description": "24x7",
            "address": "Ranipet",
            "latitude": "12.924900",
            "longitude": "79.333000",
            "is_available": "on",
        }
        base.update(extra)
        return base

    def test_profile_saves_valid_gps(self):
        response = self.client.post(reverse("provider_profile"), self.data())
        self.assertRedirects(response, reverse("provider_dashboard"))
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.latitude, Decimal("12.924900"))

    def test_invalid_gps_rejected(self):
        response = self.client.post(reverse("provider_profile"), self.data(latitude="100"))
        self.assertEqual(response.status_code, 200)
        self.provider.refresh_from_db()
        self.assertIsNone(self.provider.latitude)

    def test_only_one_coordinate_rejected(self):
        response = self.client.post(reverse("provider_profile"), self.data(longitude=""))
        self.assertEqual(response.status_code, 200)

    def test_cannot_be_available_without_gps(self):
        response = self.client.post(
            reverse("provider_profile"), self.data(latitude="", longitude="")
        )
        self.assertEqual(response.status_code, 200)

    def test_unavailable_without_gps_is_allowed(self):
        data = self.data(latitude="", longitude="")
        data.pop("is_available")
        response = self.client.post(reverse("provider_profile"), data)
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# Provider dashboard and map
# ---------------------------------------------------------------------------

class ProviderDashboardTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.provider = make_provider()
        self.client.force_login(self.provider.user)

    def test_lists_only_requests_within_10km(self):
        near = make_request(self.customer, lat_km=4)
        make_request(self.customer, lat_km=15)
        response = self.client.get(reverse("provider_dashboard"))
        self.assertEqual([r.pk for r in response.context["open_requests"]], [near.pk])
        self.assertContains(response, f"Request #{near.pk}")

    def test_shows_assigned_requests(self):
        mine = make_request(self.customer, status="ACCEPTED", provider=self.provider)
        theirs = make_request(self.customer, status="ACCEPTED", provider=make_provider("p2"))
        response = self.client.get(reverse("provider_dashboard"))
        self.assertEqual([r.pk for r in response.context["assigned_requests"]], [mine.pk])
        self.assertNotIn(theirs, response.context["assigned_requests"])

    def test_missing_location_warning(self):
        self.provider.latitude = None
        self.provider.longitude = None
        self.provider.save()
        response = self.client.get(reverse("provider_dashboard"))
        self.assertContains(response, "GPS location is missing")

    def test_map_data_contains_request_coordinates(self):
        near = make_request(self.customer, lat_km=4)
        response = self.client.get(reverse("provider_dashboard"))
        markers = response.context["map_data"]["requests"]
        self.assertEqual(markers[0]["id"], near.pk)
        self.assertAlmostEqual(markers[0]["lat"], float(near.latitude), places=5)
        self.assertContains(response, 'id="map-data"')


class MapViewTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.provider = make_provider()

    def test_provider_map_shows_nearby_open_requests(self):
        near = make_request(self.customer, lat_km=3)
        make_request(self.customer, lat_km=20)
        self.client.force_login(self.provider.user)
        response = self.client.get(reverse("map"))
        self.assertEqual(response.status_code, 200)
        data = response.context["map_data"]
        self.assertEqual(data["mode"], "provider")
        self.assertEqual([r["id"] for r in data["requests"]], [near.pk])
        self.assertEqual(data["radius_km"], 10)

    def test_customer_map_shows_available_providers_with_gps(self):
        make_provider("away", available=False)
        make_provider("nogps", lat=None, lng=None)
        self.client.force_login(self.customer)
        response = self.client.get(reverse("map"))
        self.assertEqual(response.status_code, 200)
        data = response.context["map_data"]
        self.assertEqual(data["mode"], "customer")
        self.assertEqual([p["name"] for p in data["providers"]], ["provider1 garage"])

    def test_map_json_is_escaped_safely(self):
        make_request(self.customer, lat_km=2, vehicle="</script><script>alert(1)</script>")
        self.client.force_login(self.provider.user)
        response = self.client.get(reverse("map"))
        self.assertNotContains(response, "</script><script>alert(1)")


# ---------------------------------------------------------------------------
# Accept / reject / status workflow
# ---------------------------------------------------------------------------

class AcceptRequestTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.p1 = make_provider("p1")
        self.p2 = make_provider("p2")
        self.req = make_request(self.customer, lat_km=3)

    def accept(self, provider):
        self.client.force_login(provider.user)
        return self.client.post(reverse("accept_request", args=[self.req.pk]))

    def test_provider_can_accept_nearby_request(self):
        response = self.accept(self.p1)
        self.assertRedirects(response, reverse("request_detail", args=[self.req.pk]))
        self.req.refresh_from_db()
        self.assertEqual(self.req.provider, self.p1)
        self.assertEqual(self.req.status, "ACCEPTED")
        self.assertIsNotNone(self.req.accepted_at)

    def test_second_provider_cannot_accept_same_request(self):
        self.accept(self.p1)
        response = self.accept(self.p2)
        self.assertRedirects(response, reverse("provider_dashboard"))
        self.assertTrue(any("already been accepted" in m for m in message_texts(response)))
        self.req.refresh_from_db()
        self.assertEqual(self.req.provider, self.p1)

    def test_same_provider_cannot_accept_twice(self):
        self.accept(self.p1)
        self.accept(self.p1)
        self.req.refresh_from_db()
        self.assertEqual(self.req.provider, self.p1)
        self.assertEqual(AssistanceRequest.objects.filter(provider=self.p1).count(), 1)

    def test_conditional_update_only_succeeds_once(self):
        """The database-level guard behind accept_request."""
        qs = AssistanceRequest.objects.filter(pk=self.req.pk, status="OPEN", provider__isnull=True)
        self.assertEqual(qs.update(provider=self.p1, status="ACCEPTED"), 1)
        self.assertEqual(qs.update(provider=self.p2, status="ACCEPTED"), 0)

    def test_accepted_request_disappears_from_other_providers_list(self):
        self.accept(self.p1)
        self.client.force_login(self.p2.user)
        response = self.client.get(reverse("provider_dashboard"))
        self.assertEqual(list(response.context["open_requests"]), [])

    def test_provider_beyond_10km_cannot_accept_even_by_direct_post(self):
        far = make_provider("far", lat=offset(25))
        response = self.accept(far)
        self.assertRedirects(response, reverse("provider_dashboard"))
        self.assertTrue(any("10 km" in m for m in message_texts(response)))
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "OPEN")

    def test_unavailable_provider_cannot_accept(self):
        away = make_provider("away", available=False)
        self.accept(away)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "OPEN")

    def test_provider_without_gps_cannot_accept(self):
        nogps = make_provider("nogps", lat=None, lng=None)
        self.accept(nogps)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "OPEN")

    def test_service_type_mismatch_cannot_accept(self):
        towing_only = make_provider("tow", service_type="TOWING")
        mech_req = make_request(self.customer, lat_km=2, service="MECHANIC")
        self.client.force_login(towing_only.user)
        self.client.post(reverse("accept_request", args=[mech_req.pk]))
        mech_req.refresh_from_db()
        self.assertEqual(mech_req.status, "OPEN")

    def test_cannot_accept_request_without_gps(self):
        no_gps_req = make_request(self.customer, lat_km=None)
        self.client.force_login(self.p1.user)
        self.client.post(reverse("accept_request", args=[no_gps_req.pk]))
        no_gps_req.refresh_from_db()
        self.assertEqual(no_gps_req.status, "OPEN")

    def test_cannot_accept_cancelled_request(self):
        self.req.status = "CANCELLED"
        self.req.save()
        self.accept(self.p1)
        self.req.refresh_from_db()
        self.assertIsNone(self.req.provider)

    def test_cannot_accept_after_rejecting(self):
        RequestRejection.objects.create(request=self.req, provider=self.p1)
        self.accept(self.p1)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "OPEN")

    def test_accept_unknown_request_returns_404(self):
        self.client.force_login(self.p1.user)
        self.assertEqual(self.client.post(reverse("accept_request", args=[99999])).status_code, 404)

    def test_customer_sees_assigned_provider_details(self):
        self.accept(self.p1)
        self.client.force_login(self.customer)
        response = self.client.get(reverse("request_detail", args=[self.req.pk]))
        self.assertContains(response, "p1 garage")
        self.assertContains(response, "9000000000")
        self.assertContains(response, "Provider Assigned")


class RejectRequestTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.p1 = make_provider("p1")
        self.p2 = make_provider("p2")
        self.req = make_request(self.customer, lat_km=3)

    def test_reject_hides_request_from_that_provider_only(self):
        self.client.force_login(self.p1.user)
        response = self.client.post(reverse("reject_request", args=[self.req.pk]))
        self.assertRedirects(response, reverse("provider_dashboard"))
        self.assertTrue(RequestRejection.objects.filter(request=self.req, provider=self.p1).exists())

        self.assertEqual(list(self.client.get(reverse("provider_dashboard")).context["open_requests"]), [])
        self.client.force_login(self.p2.user)
        listed = self.client.get(reverse("provider_dashboard")).context["open_requests"]
        self.assertEqual([r.pk for r in listed], [self.req.pk])

    def test_reject_does_not_change_request_status(self):
        self.client.force_login(self.p1.user)
        self.client.post(reverse("reject_request", args=[self.req.pk]))
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "OPEN")
        self.assertIsNone(self.req.provider)

    def test_reject_twice_is_harmless(self):
        self.client.force_login(self.p1.user)
        self.client.post(reverse("reject_request", args=[self.req.pk]))
        self.client.post(reverse("reject_request", args=[self.req.pk]))
        self.assertEqual(RequestRejection.objects.filter(request=self.req).count(), 1)

    def test_cannot_reject_already_accepted_request(self):
        self.req.provider = self.p2
        self.req.status = "ACCEPTED"
        self.req.save()
        self.client.force_login(self.p1.user)
        self.client.post(reverse("reject_request", args=[self.req.pk]))
        self.assertFalse(RequestRejection.objects.exists())

    def test_other_providers_can_still_accept_after_a_rejection(self):
        self.client.force_login(self.p1.user)
        self.client.post(reverse("reject_request", args=[self.req.pk]))
        self.client.force_login(self.p2.user)
        self.client.post(reverse("accept_request", args=[self.req.pk]))
        self.req.refresh_from_db()
        self.assertEqual(self.req.provider, self.p2)


class StatusWorkflowTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.provider = make_provider()
        self.other = make_provider("other")
        self.req = make_request(
            self.customer, lat_km=3, status="ACCEPTED", provider=self.provider
        )

    def post_status(self, status, user=None, **extra):
        self.client.force_login(user or self.provider.user)
        return self.client.post(
            reverse("update_status", args=[self.req.pk]), {"status": status, **extra}
        )

    def test_full_valid_workflow(self):
        self.post_status("IN_PROGRESS")
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "IN_PROGRESS")
        self.assertIsNotNone(self.req.started_at)

        self.post_status("RESOLVED", progress_note="Replaced battery")
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "RESOLVED")
        self.assertIsNotNone(self.req.completed_at)
        self.assertEqual(self.req.progress_note, "Replaced battery")

    def test_cannot_skip_in_progress(self):
        self.post_status("RESOLVED")
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "ACCEPTED")

    def test_cannot_go_backwards(self):
        self.req.status = "RESOLVED"
        self.req.save()
        self.post_status("IN_PROGRESS")
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "RESOLVED")

    def test_cannot_reopen_or_set_arbitrary_status(self):
        for bad in ("OPEN", "CANCELLED", "ACCEPTED", "HACKED", ""):
            with self.subTest(status=bad):
                self.post_status(bad)
                self.req.refresh_from_db()
                self.assertEqual(self.req.status, "ACCEPTED")

    def test_cannot_change_cancelled_request(self):
        self.req.status = "CANCELLED"
        self.req.save()
        self.post_status("IN_PROGRESS")
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "CANCELLED")

    def test_unassigned_provider_cannot_update(self):
        response = self.post_status("IN_PROGRESS", user=self.other.user)
        self.assertEqual(response.status_code, 403)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "ACCEPTED")

    def test_customer_sees_progress(self):
        self.post_status("IN_PROGRESS", progress_note="On site")
        self.client.force_login(self.customer)
        response = self.client.get(reverse("request_detail", args=[self.req.pk]))
        self.assertContains(response, "Service in Progress")
        self.assertContains(response, "On site")

    def test_customer_sees_completed_details(self):
        self.post_status("IN_PROGRESS")
        self.post_status("RESOLVED")
        self.client.force_login(self.customer)
        response = self.client.get(reverse("request_detail", args=[self.req.pk]))
        self.assertContains(response, "Assistance Completed")
        self.assertContains(response, reverse("download_invoice", args=[self.req.pk]))

    def test_progress_note_is_html_escaped(self):
        self.post_status("IN_PROGRESS", progress_note="<script>alert(1)</script>")
        self.client.force_login(self.customer)
        response = self.client.get(reverse("request_detail", args=[self.req.pk]))
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_progress_note_endpoint(self):
        self.client.force_login(self.provider.user)
        self.client.post(reverse("update_progress_note", args=[self.req.pk]), {"progress_note": "Arriving in 10 min"})
        self.req.refresh_from_db()
        self.assertEqual(self.req.progress_note, "Arriving in 10 min")


class CancelRequestTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.provider = make_provider()

    def test_customer_can_cancel_open_request(self):
        req = make_request(self.customer)
        self.client.force_login(self.customer)
        self.client.post(reverse("cancel_request", args=[req.pk]))
        req.refresh_from_db()
        self.assertEqual(req.status, "CANCELLED")

    def test_cannot_cancel_after_work_started(self):
        req = make_request(self.customer, status="IN_PROGRESS", provider=self.provider)
        self.client.force_login(self.customer)
        self.client.post(reverse("cancel_request", args=[req.pk]))
        req.refresh_from_db()
        self.assertEqual(req.status, "IN_PROGRESS")

    def test_other_customer_cannot_cancel(self):
        req = make_request(self.customer)
        intruder = make_customer("intruder")
        self.client.force_login(intruder)
        response = self.client.post(reverse("cancel_request", args=[req.pk]))
        self.assertEqual(response.status_code, 404)
        req.refresh_from_db()
        self.assertEqual(req.status, "OPEN")


# ---------------------------------------------------------------------------
# Request detail visibility
# ---------------------------------------------------------------------------

class RequestDetailAccessTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.provider = make_provider()
        self.req = make_request(self.customer, lat_km=3)

    def get(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("request_detail", args=[self.req.pk]))

    def test_owner_can_view(self):
        self.assertEqual(self.get(self.customer).status_code, 200)

    def test_other_customer_blocked(self):
        self.assertEqual(self.get(make_customer("stranger")).status_code, 403)

    def test_nearby_provider_can_preview_open_request_without_phone(self):
        response = self.get(self.provider.user)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accept request")
        self.assertContains(response, "Shown after you accept")
        self.assertNotContains(response, 'href="tel:9000000001"')

    def test_far_provider_cannot_view_open_request(self):
        far = make_provider("far", lat=offset(30))
        self.assertEqual(self.get(far.user).status_code, 403)

    def test_assigned_provider_sees_customer_phone(self):
        self.req.provider = self.provider
        self.req.status = "ACCEPTED"
        self.req.save()
        response = self.get(self.provider.user)
        self.assertContains(response, "9000000001")

    def test_other_provider_blocked_after_assignment(self):
        self.req.provider = self.provider
        self.req.status = "ACCEPTED"
        self.req.save()
        other = make_provider("other")
        self.assertEqual(self.get(other.user).status_code, 403)

    def test_staff_can_view(self):
        staff = User.objects.create_user("staff", password=PASSWORD, is_staff=True)
        self.assertEqual(self.get(staff).status_code, 200)

    def test_missing_request_404(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("request_detail", args=[99999])).status_code, 404)


# ---------------------------------------------------------------------------
# PDF receipt
# ---------------------------------------------------------------------------

class ReceiptTests(TestCase):
    def setUp(self):
        self.customer = make_customer()
        self.provider = make_provider()
        self.req = make_request(
            self.customer, status="RESOLVED", provider=self.provider,
            issue_description="Battery <dead> & \"flat\" -- 100% broken",
        )

    def test_owner_downloads_valid_pdf(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("download_invoice", args=[self.req.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(f"RoadGuard_Receipt_{self.req.pk}.pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertGreater(len(response.content), 1500)

    def test_pdf_works_for_open_request_without_provider(self):
        open_req = make_request(self.customer)
        self.client.force_login(self.customer)
        response = self.client.get(reverse("download_invoice", args=[open_req.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_pdf_survives_markup_characters_and_missing_fields(self):
        sparse = make_request(self.customer, location_text="", city="", district="", state="", vehicle="<b>X</b>")
        self.client.force_login(self.customer)
        response = self.client.get(reverse("download_invoice", args=[sparse.pk]))
        self.assertEqual(response.status_code, 200)

    def test_other_customer_cannot_download(self):
        self.client.force_login(make_customer("stranger"))
        self.assertEqual(self.client.get(reverse("download_invoice", args=[self.req.pk])).status_code, 403)

    def test_provider_cannot_download(self):
        self.client.force_login(self.provider.user)
        self.assertEqual(self.client.get(reverse("download_invoice", args=[self.req.pk])).status_code, 403)

    def test_staff_can_download(self):
        staff = User.objects.create_user("staff", password=PASSWORD, is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("download_invoice", args=[self.req.pk])).status_code, 200)


# ---------------------------------------------------------------------------
# Complete end-to-end workflow (checklist section 4)
# ---------------------------------------------------------------------------

class EndToEndWorkflowTests(TestCase):
    def test_full_customer_provider_flow(self):
        customer = make_customer()
        p1, p2 = make_provider("p1"), make_provider("p2")

        # 1-2. customer creates a request
        self.client.force_login(customer)
        self.client.post(reverse("create_request"), {
            "service_needed": "EITHER", "vehicle": "Activa", "issue_description": "Puncture",
            "phone": "9876543210", "state": "Tamil Nadu", "district": "Ranipet", "city": "Ranipet",
            "location_text": "NH48", "latitude": str(offset(2)), "longitude": str(BASE_LNG),
        })
        req = AssistanceRequest.objects.get()

        # 3. both eligible providers can see it
        for p in (p1, p2):
            self.client.force_login(p.user)
            listed = self.client.get(reverse("provider_dashboard")).context["open_requests"]
            self.assertEqual([r.pk for r in listed], [req.pk])

        # 4-5. p1 accepts, p2 can no longer accept
        self.client.force_login(p1.user)
        self.client.post(reverse("accept_request", args=[req.pk]))
        self.client.force_login(p2.user)
        self.client.post(reverse("accept_request", args=[req.pk]))
        req.refresh_from_db()
        self.assertEqual(req.provider, p1)

        # 6. customer sees provider info
        self.client.force_login(customer)
        self.assertContains(self.client.get(reverse("request_detail", args=[req.pk])), "p1 garage")

        # 7-9. provider starts and completes
        self.client.force_login(p1.user)
        self.client.post(reverse("update_status", args=[req.pk]), {"status": "IN_PROGRESS"})
        self.client.post(reverse("update_status", args=[req.pk]), {"status": "RESOLVED", "progress_note": "Done"})
        req.refresh_from_db()
        self.assertEqual(req.status, "RESOLVED")

        # 10-11. customer views completed request and downloads the receipt
        self.client.force_login(customer)
        self.assertContains(self.client.get(reverse("request_detail", args=[req.pk])), "Assistance Completed")
        pdf = self.client.get(reverse("download_invoice", args=[req.pk]))
        self.assertTrue(pdf.content.startswith(b"%PDF"))


# ---------------------------------------------------------------------------
# PWA
# ---------------------------------------------------------------------------

class PWATests(TestCase):
    def test_manifest_is_valid_json_with_icons(self):
        response = self.client.get(reverse("manifest"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("manifest+json", response["Content-Type"])
        data = json.loads(response.content)
        self.assertEqual(data["display"], "standalone")
        self.assertEqual(data["start_url"], "/")
        self.assertEqual(data["scope"], "/")
        self.assertEqual(data["short_name"], "RoadGuard")
        sizes = {icon["sizes"] for icon in data["icons"]}
        self.assertIn("192x192", sizes)
        self.assertIn("512x512", sizes)
        for icon in data["icons"]:
            self.assertTrue(icon["src"].startswith("/static/icons/"))

    def test_manifest_icon_files_exist(self):
        from django.contrib.staticfiles import finders
        for icon in json.loads(self.client.get(reverse("manifest")).content)["icons"]:
            path = icon["src"].replace("/static/", "", 1)
            self.assertIsNotNone(finders.find(path), f"missing {path}")

    def test_service_worker_served_from_root_with_scope_header(self):
        response = self.client.get("/service-worker.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response["Content-Type"])
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertIn("no-cache", response["Cache-Control"])

    def test_service_worker_never_caches_html_pages(self):
        body = self.client.get("/service-worker.js").content.decode()
        self.assertIn('request.mode === "navigate"', body)
        self.assertNotIn('addAll(["/"])', body)
        self.assertIn("/offline/", body)
        self.assertIn('roadguard-shell-v3', body)
        self.assertIn('request.method !== "GET"', body)
        self.assertIn('url.pathname.startsWith("/static/")', body)

    def test_offline_page_loads(self):
        self.assertEqual(self.client.get(reverse("offline")).status_code, 200)

    def test_pages_link_manifest_and_register_worker(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'rel="manifest"')
        self.assertContains(response, "js/app.js")
        self.assertContains(response, 'apple-mobile-web-app-capable')
        self.assertContains(response, 'id="pwaInstallButton"')
        self.assertContains(response, 'id="pwaInstallDialog"')


class PublicPageTests(TestCase):
    def test_home_page_loads(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_static_files_referenced_by_base_exist(self):
        from django.contrib.staticfiles import finders
        for path in ("css/style.css", "js/app.js", "js/rg-map.js", "icons/icon-192.png"):
            self.assertIsNotNone(finders.find(path), path)
