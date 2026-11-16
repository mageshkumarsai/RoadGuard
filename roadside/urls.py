
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    # Home
    path("", views.home, name="home"),

    # Registration
    path("register/", views.register, name="register"),

    # Login
    path("login/", views.role_login, name="login"),
    path("customer-login/", views.customer_login, name="customer_login"),
    path("provider-login/", views.provider_login, name="provider_login"),

    # Logout
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "customer-dashboard/",
        views.customer_dashboard,
        name="customer_dashboard",
    ),
    path(
        "provider-dashboard/",
        views.provider_dashboard,
        name="provider_dashboard",
    ),

    # Assistance requests
    path(
        "create-request/",
        views.create_request,
        name="create_request",
    ),
    path(
        "request/<int:pk>/",
        views.request_detail,
        name="request_detail",
    ),
    path(
        "request/<int:pk>/accept/",
        views.accept_request,
        name="accept_request",
    ),
    path(
        "request/<int:pk>/reject/",
        views.reject_request,
        name="reject_request",
    ),
    path(
        "request/<int:pk>/cancel/",
        views.cancel_request,
        name="cancel_request",
    ),
    path(
        "request/<int:pk>/update-status/",
        views.update_status,
        name="update_status",
    ),
    path(
        "request/<int:pk>/progress-note/",
        views.update_progress_note,
        name="update_progress_note",
    ),

    # PDF receipt download
    path(
        "request/<int:pk>/invoice/",
        views.download_invoice,
        name="download_invoice",
    ),

    # Provider profile
    path(
        "provider-profile/",
        views.provider_profile,
        name="provider_profile",
    ),

    # Map
    path("map/", views.map_view, name="map"),

    # PWA manifest
    path("manifest.json", views.manifest, name="manifest"),
    path("service-worker.js", views.service_worker, name="service_worker"),
    path("offline/", views.offline, name="offline"),
]
