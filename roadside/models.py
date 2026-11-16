
from django.conf import settings
from django.db import models


class Provider(models.Model):

    SERVICE_TYPES = [
        ("MECHANIC", "Mechanic"),
        ("TOWING", "Towing service"),
        ("BOTH", "Mechanic and towing"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_profile"
    )

    business_name = models.CharField(max_length=120)
    service_type = models.CharField(max_length=12, choices=SERVICE_TYPES)
    phone = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name


class AssistanceRequest(models.Model):

    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("ACCEPTED", "Accepted"),
        ("IN_PROGRESS", "In progress"),
        ("RESOLVED", "Resolved"),
        ("CANCELLED", "Cancelled"),
    ]

    SERVICE_CHOICES = [
        ("MECHANIC", "Mechanic"),
        ("TOWING", "Towing"),
        ("EITHER", "Mechanic or towing"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistance_requests"
    )

    provider = models.ForeignKey(
        Provider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests"
    )

    service_needed = models.CharField(
        max_length=12,
        choices=SERVICE_CHOICES,
        default="EITHER"
    )

    vehicle = models.CharField(max_length=100)
    issue_description = models.TextField()
    phone = models.CharField(max_length=20)

    # Location details
    location_text = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="OPEN"
    )

    # Work progress (added for the request workflow)
    progress_note = models.TextField(blank=True, default="")
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Allowed status changes. Anything not listed here is rejected.
    PROVIDER_TRANSITIONS = {
        "ACCEPTED": ("IN_PROGRESS", "Start service"),
        "IN_PROGRESS": ("RESOLVED", "Mark as completed"),
    }
    CUSTOMER_CANCELLABLE = ("OPEN", "ACCEPTED")
    ACTIVE_STATUSES = ("OPEN", "ACCEPTED", "IN_PROGRESS")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Request #{self.pk} - {self.customer.username}"

    @property
    def next_provider_step(self):
        """(new_status, button_label) the provider may apply now, or None."""
        return self.PROVIDER_TRANSITIONS.get(self.status)

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES


class RequestRejection(models.Model):
    """A provider declined an open request; it is hidden from that provider."""

    request = models.ForeignKey(
        AssistanceRequest, on_delete=models.CASCADE, related_name="rejections"
    )
    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="rejections"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["request", "provider"],
                name="unique_rejection_per_provider",
            )
        ]

    def __str__(self):
        return f"{self.provider} rejected request #{self.request_id}"
