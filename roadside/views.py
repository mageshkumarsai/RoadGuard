from functools import wraps
from io import BytesIO
from xml.sax.saxutils import escape

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import AssistanceRequestForm, ProviderProfileForm, RegistrationForm
from .models import AssistanceRequest, Provider, RequestRejection
from .utils import (  # noqa: F401  (calculate_distance re-exported for old imports)
    NEARBY_RADIUS_KM,
    calculate_distance,
    distance_to_request,
    is_valid_coordinate,
    nearby_open_requests,
    service_matches,
    to_float,
)


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def is_provider(user):
    return user.is_authenticated and hasattr(user, "provider_profile")


def forbidden(request, message):
    return render(
        request, "errors/forbidden.html", {"message": message}, status=403
    )


def provider_required(view):
    """Only logged-in service providers may open the view."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_provider(request.user):
            return forbidden(request, "This page is only available to service providers.")
        return view(request, *args, **kwargs)

    return login_required(wrapper)


def customer_required(view):
    """Only logged-in customers (non-providers) may open the view."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if is_provider(request.user):
            return forbidden(request, "This page is only available to vehicle owners (customers).")
        return view(request, *args, **kwargs)

    return login_required(wrapper)


# ---------------------------------------------------------------------------
# Public pages and authentication
# ---------------------------------------------------------------------------

def home(request):
    providers = Provider.objects.filter(is_available=True)[:6]
    return render(request, "roadside/home.html", {"providers": providers})


def role_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "registration/role_login.html")


def _login_view(request, role):
    """Shared login logic. role is 'customer' or 'provider'."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            user_is_provider = hasattr(user, "provider_profile")

            if role == "customer" and user_is_provider:
                messages.error(
                    request,
                    "This is a service provider account. Please use the Provider login.",
                )
            elif role == "provider" and not user_is_provider:
                messages.error(
                    request,
                    "This is a customer account. Please use the Customer login.",
                )
            else:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                return redirect("dashboard")
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "registration/login.html",
        {"form": form, "login_role": role.upper()},
    )


def customer_login(request):
    return _login_view(request, "customer")


def provider_login(request):
    return _login_view(request, "provider")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                if form.cleaned_data.get("role") == "PROVIDER":
                    Provider.objects.create(
                        user=user,
                        business_name=form.cleaned_data["business_name"],
                        service_type=form.cleaned_data["service_type"],
                        phone=form.cleaned_data["phone"],
                    )

            login(request, user)
            messages.success(request, "Registration successful!")
            if is_provider(user):
                messages.info(
                    request,
                    "Add your GPS location in your provider profile to start "
                    "receiving requests within 10 km.",
                )
            return redirect("dashboard")
    else:
        form = RegistrationForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    if is_provider(request.user):
        return redirect("provider_dashboard")
    return redirect("customer_dashboard")


# ---------------------------------------------------------------------------
# Customer views
# ---------------------------------------------------------------------------

@customer_required
def customer_dashboard(request):
    all_requests = list(
        AssistanceRequest.objects.filter(customer=request.user).select_related("provider")
    )
    active = [r for r in all_requests if r.is_active]
    completed = [r for r in all_requests if r.status == "RESOLVED"]

    return render(
        request,
        "roadside/customer_dashboard.html",
        {
            "requests": all_requests,
            "active_requests": active,
            "completed_count": len(completed),
            "total_count": len(all_requests),
        },
    )


@customer_required
def create_request(request):
    if request.method == "POST":
        form = AssistanceRequestForm(request.POST)

        if form.is_valid():
            item = form.save(commit=False)
            item.customer = request.user
            item.save()

            messages.success(request, "Your assistance request was submitted!")
            return redirect("request_detail", pk=item.pk)
    else:
        form = AssistanceRequestForm()

    return render(request, "roadside/create_request.html", {"form": form})


@customer_required
@require_POST
def cancel_request(request, pk):
    item = get_object_or_404(AssistanceRequest, pk=pk, customer=request.user)

    with transaction.atomic():
        item = AssistanceRequest.objects.select_for_update().get(pk=pk)
        if item.status in AssistanceRequest.CUSTOMER_CANCELLABLE:
            item.status = "CANCELLED"
            item.save()
            messages.success(request, "Your request has been cancelled.")
        else:
            messages.error(
                request,
                "This request can no longer be cancelled because work has already started.",
            )

    return redirect("request_detail", pk=pk)


# ---------------------------------------------------------------------------
# Request detail (customer, assigned provider, eligible provider, staff)
# ---------------------------------------------------------------------------

@login_required
def request_detail(request, pk):
    item = get_object_or_404(
        AssistanceRequest.objects.select_related("customer", "provider"), pk=pk
    )

    user = request.user
    provider = user.provider_profile if is_provider(user) else None

    is_owner = item.customer_id == user.id
    is_assigned_provider = bool(provider and item.provider_id == provider.id)

    # A provider may preview an open request only if it is within range of them.
    distance = None
    is_eligible_provider = False
    if provider and item.status == "OPEN" and item.provider_id is None:
        distance = distance_to_request(provider, item)
        is_eligible_provider = (
            provider.is_available
            and service_matches(provider, item)
            and distance is not None
            and distance <= NEARBY_RADIUS_KM
            and not RequestRejection.objects.filter(request=item, provider=provider).exists()
        )

    if not (is_owner or is_assigned_provider or is_eligible_provider or user.is_staff):
        return forbidden(request, "You are not allowed to view this request.")

    if is_assigned_provider and distance is None:
        distance = distance_to_request(provider, item)

    context = {
        "item": item,
        "is_owner": is_owner,
        "is_assigned_provider": is_assigned_provider,
        "is_eligible_provider": is_eligible_provider,
        "show_contact": is_owner or is_assigned_provider or user.is_staff,
        "distance_km": round(distance, 1) if distance is not None else None,
        "next_step": item.next_provider_step,
        "can_cancel": is_owner and item.status in AssistanceRequest.CUSTOMER_CANCELLABLE,
        "can_download_receipt": is_owner or user.is_staff,
    }
    return render(request, "roadside/request_detail.html", context)


# ---------------------------------------------------------------------------
# Provider views
# ---------------------------------------------------------------------------

@provider_required
def provider_dashboard(request):
    provider = request.user.provider_profile

    open_requests = nearby_open_requests(provider)
    my_requests = list(
        AssistanceRequest.objects.filter(provider=provider).select_related("customer")
    )
    active = [r for r in my_requests if r.status in ("ACCEPTED", "IN_PROGRESS")]
    completed = [r for r in my_requests if r.status == "RESOLVED"]

    has_location = is_valid_coordinate(provider.latitude, provider.longitude)

    map_data = {
        "mode": "provider",
        "radius_km": NEARBY_RADIUS_KM,
        "center": (
            [to_float(provider.latitude), to_float(provider.longitude)]
            if has_location
            else None
        ),
        "requests": [_request_marker(r) for r in open_requests],
        "assigned": [
            _request_marker(r)
            for r in active
            if is_valid_coordinate(r.latitude, r.longitude)
        ],
    }

    return render(
        request,
        "roadside/provider_dashboard.html",
        {
            "provider": provider,
            "has_location": has_location,
            "open_requests": open_requests,
            "assigned_requests": active,
            "completed_requests": completed,
            "radius_km": NEARBY_RADIUS_KM,
            "map_data": map_data,
        },
    )


def _request_marker(item):
    from django.urls import reverse

    return {
        "id": item.pk,
        "lat": to_float(item.latitude),
        "lng": to_float(item.longitude),
        "vehicle": item.vehicle,
        "service": item.get_service_needed_display(),
        "issue": item.issue_description[:140],
        "location": ", ".join(p for p in (item.location_text, item.city, item.district) if p),
        "distance": getattr(item, "distance_km", None),
        "status": item.get_status_display(),
        "url": reverse("request_detail", args=[item.pk]),
    }


@provider_required
@require_POST
def accept_request(request, pk):
    provider = request.user.provider_profile

    if not provider.is_available:
        messages.error(request, "You are currently marked unavailable.")
        return redirect("provider_dashboard")

    if not is_valid_coordinate(provider.latitude, provider.longitude):
        messages.error(
            request, "Add your GPS location in your profile before accepting requests."
        )
        return redirect("provider_profile")

    with transaction.atomic():
        # Lock the row so two providers cannot process it at the same time.
        item = get_object_or_404(AssistanceRequest.objects.select_for_update(), pk=pk)

        if item.status != "OPEN" or item.provider_id is not None:
            messages.error(request, "This request has already been accepted by another provider.")
            return redirect("provider_dashboard")

        if RequestRejection.objects.filter(request=item, provider=provider).exists():
            messages.error(request, "You rejected this request earlier.")
            return redirect("provider_dashboard")

        if not service_matches(provider, item):
            messages.error(request, "This request does not match your service type.")
            return redirect("provider_dashboard")

        distance = distance_to_request(provider, item)
        if distance is None:
            messages.error(request, "This request has no valid GPS location.")
            return redirect("provider_dashboard")
        if distance > NEARBY_RADIUS_KM:
            messages.error(
                request,
                f"This request is {distance:.1f} km away. You can only accept "
                f"requests within {NEARBY_RADIUS_KM} km.",
            )
            return redirect("provider_dashboard")

        # Conditional UPDATE: succeeds for exactly one provider.
        now = timezone.now()
        updated = AssistanceRequest.objects.filter(
            pk=item.pk, status="OPEN", provider__isnull=True
        ).update(provider=provider, status="ACCEPTED", accepted_at=now, updated_at=now)

    if updated != 1:
        messages.error(request, "This request has already been accepted by another provider.")
        return redirect("provider_dashboard")

    messages.success(request, "Request accepted. Contact the customer and head to the location.")
    return redirect("request_detail", pk=pk)


@provider_required
@require_POST
def reject_request(request, pk):
    provider = request.user.provider_profile
    item = get_object_or_404(AssistanceRequest, pk=pk)

    if item.status != "OPEN" or item.provider_id is not None:
        messages.error(request, "This request is no longer open.")
        return redirect("provider_dashboard")

    RequestRejection.objects.get_or_create(request=item, provider=provider)
    messages.info(request, f"Request #{item.pk} rejected. It will not appear in your list again.")
    return redirect("provider_dashboard")


@login_required
@require_POST
def update_status(request, pk):
    with transaction.atomic():
        item = get_object_or_404(AssistanceRequest.objects.select_for_update(), pk=pk)

        is_assigned_provider = (
            is_provider(request.user) and item.provider_id == request.user.provider_profile.id
        )

        if not (is_assigned_provider or request.user.is_staff):
            return forbidden(request, "You cannot update this request.")

        new_status = request.POST.get("status", "")
        step = item.next_provider_step

        if step is None or new_status != step[0]:
            messages.error(
                request,
                f"Invalid status change. A request that is "
                f"{item.get_status_display().lower()} cannot be moved to "
                f"'{new_status or 'blank'}'.",
            )
            return redirect("request_detail", pk=item.pk)

        now = timezone.now()
        item.status = new_status
        if new_status == "IN_PROGRESS":
            item.started_at = now
        elif new_status == "RESOLVED":
            item.completed_at = now

        note = request.POST.get("progress_note", "").strip()[:500]
        if note:
            item.progress_note = note
        item.save()

    messages.success(request, f"Status updated to {item.get_status_display()}.")
    return redirect("request_detail", pk=item.pk)


@provider_required
@require_POST
def update_progress_note(request, pk):
    item = get_object_or_404(AssistanceRequest, pk=pk, provider=request.user.provider_profile)

    if item.status not in ("ACCEPTED", "IN_PROGRESS"):
        messages.error(request, "Progress notes can only be added while the job is active.")
    else:
        item.progress_note = request.POST.get("progress_note", "").strip()[:500]
        item.save()
        messages.success(request, "Progress note saved. The customer can see it.")
    return redirect("request_detail", pk=item.pk)


@provider_required
def provider_profile(request):
    provider = request.user.provider_profile

    if request.method == "POST":
        form = ProviderProfileForm(request.POST, instance=provider)

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("provider_dashboard")
    else:
        form = ProviderProfileForm(instance=provider)

    return render(request, "roadside/provider_profile.html", {"form": form})


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

@login_required
def map_view(request):
    if is_provider(request.user):
        provider = request.user.provider_profile
        has_location = is_valid_coordinate(provider.latitude, provider.longitude)
        data = {
            "mode": "provider",
            "radius_km": NEARBY_RADIUS_KM,
            "center": (
                [to_float(provider.latitude), to_float(provider.longitude)]
                if has_location
                else None
            ),
            "requests": [_request_marker(r) for r in nearby_open_requests(provider)],
            "assigned": [
                _request_marker(r)
                for r in AssistanceRequest.objects.filter(
                    provider=provider, status__in=("ACCEPTED", "IN_PROGRESS")
                )
                if is_valid_coordinate(r.latitude, r.longitude)
            ],
        }
        return render(
            request,
            "roadside/map.html",
            {"map_data": data, "is_provider": True, "has_location": has_location},
        )

    providers = Provider.objects.filter(
        is_available=True, latitude__isnull=False, longitude__isnull=False
    )
    data = {
        "mode": "customer",
        "providers": [
            {
                "name": p.business_name,
                "service": p.get_service_type_display(),
                "phone": p.phone,
                "lat": to_float(p.latitude),
                "lng": to_float(p.longitude),
            }
            for p in providers
            if is_valid_coordinate(p.latitude, p.longitude)
        ],
    }
    return render(
        request, "roadside/map.html", {"map_data": data, "is_provider": False}
    )


# ---------------------------------------------------------------------------
# PDF receipt
# ---------------------------------------------------------------------------

def _safe(value, default="Not provided"):
    """Escape text for ReportLab's mini-markup so user input cannot break the PDF."""
    text = str(value).strip() if value not in (None, "") else ""
    return escape(text) if text else default


@login_required
def download_invoice(request, pk):
    item = get_object_or_404(
        AssistanceRequest.objects.select_related("customer", "provider"), pk=pk
    )

    # Only the customer who created this request, or staff, can download it.
    if item.customer_id != request.user.id and not request.user.is_staff:
        return forbidden(request, "You are not allowed to download this receipt.")

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"RoadGuard Receipt RG-{item.pk:05d}",
        author="RoadGuard",
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    cell = ParagraphStyle("Cell", parent=normal, fontSize=10, leading=13)
    cell_bold = ParagraphStyle("CellBold", parent=cell, fontName="Helvetica-Bold")

    title_style = ParagraphStyle(
        "RoadGuardTitle", parent=styles["Title"],
        textColor=colors.HexColor("#1565C0"), alignment=TA_CENTER, fontSize=24, spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "RoadGuardSubtitle", parent=normal, alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"), fontSize=11,
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"],
        textColor=colors.HexColor("#1565C0"), spaceBefore=12, spaceAfter=8,
    )

    def local(dt):
        return timezone.localtime(dt).strftime("%d %B %Y, %I:%M %p") if dt else "Not recorded"

    def section(heading, rows, background):
        story.append(Paragraph(heading, heading_style))
        data = [[Paragraph(label, cell_bold), Paragraph(value, cell)] for label, value in rows]
        table = Table(data, colWidths=[45 * mm, 125 * mm])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(background)),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(table)

    story = [
        Paragraph("ROADGUARD", title_style),
        Paragraph("Roadside Assistance Request Receipt", subtitle_style),
        Spacer(1, 12),
        Paragraph(f"<b>Receipt Number:</b> RG-{item.pk:05d}", normal),
        Paragraph(f"<b>Request Date:</b> {local(item.created_at)}", normal),
        Paragraph(f"<b>Current Status:</b> {escape(item.get_status_display())}", normal),
        Spacer(1, 12),
    ]

    customer_name = item.customer.get_full_name() or item.customer.username
    section(
        "Customer Details",
        [("Customer Name", _safe(customer_name)), ("Contact Phone", _safe(item.phone))],
        "#E3F2FD",
    )
    section(
        "Vehicle and Service Details",
        [
            ("Vehicle", _safe(item.vehicle)),
            ("Service Requested", _safe(item.get_service_needed_display())),
            ("Issue Description", _safe(item.issue_description)),
        ],
        "#E8F5E9",
    )
    section(
        "Breakdown Location",
        [
            ("State", _safe(item.state)),
            ("District", _safe(item.district)),
            ("City / Town", _safe(item.city)),
            ("Street / Area", _safe(item.location_text)),
            ("Latitude", _safe(item.latitude)),
            ("Longitude", _safe(item.longitude)),
        ],
        "#FFF3E0",
    )

    if item.provider:
        provider_rows = [
            ("Business Name", _safe(item.provider.business_name)),
            ("Service Type", _safe(item.provider.get_service_type_display())),
            ("Contact Phone", _safe(item.provider.phone)),
            ("Address", _safe(item.provider.address)),
        ]
    else:
        provider_rows = [("Provider", "Not assigned yet")]
    section("Service Provider Details", provider_rows, "#F3E5F5")

    section(
        "Service Timeline",
        [
            ("Requested", local(item.created_at)),
            ("Accepted", local(item.accepted_at)),
            ("Work started", local(item.started_at)),
            ("Completed", local(item.completed_at)),
            ("Provider note", _safe(item.progress_note, "None")),
        ],
        "#ECEFF1",
    )

    story.extend([
        Spacer(1, 20),
        Paragraph(
            "This document confirms the roadside assistance request recorded on "
            "RoadGuard. It is a service request receipt, not a tax invoice or proof "
            "of payment. No service charges or payments are included.",
            styles["Italic"],
        ),
        Spacer(1, 12),
        Paragraph(
            "Thank you for choosing RoadGuard!",
            ParagraphStyle(
                "Footer", parent=normal, alignment=TA_CENTER,
                textColor=colors.HexColor("#1565C0"), fontSize=12,
            ),
        ),
    ])

    document.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="RoadGuard_Receipt_{item.pk}.pdf"'
    return response


# ---------------------------------------------------------------------------
# PWA
# ---------------------------------------------------------------------------

def manifest(request):
    return render(
        request,
        "manifest.webmanifest",
        content_type="application/manifest+json",
    )


@never_cache
def service_worker(request):
    """Serve the worker from the site root so it can control every page."""
    response = render(request, "service-worker.js", content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response


def offline(request):
    return render(request, "offline.html")
