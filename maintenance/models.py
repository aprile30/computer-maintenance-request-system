from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [
        ("admin", "Administrator"),
        ("technician", "Technician"),
        ("requester", "Faculty / Staff"),
    ]
    role = models.CharField(max_length=12, choices=ROLES, default="requester")
    department = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        # a superuser made with createsuperuser should behave as Administrator
        if self.is_superuser:
            self.role = "admin"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username


class Location(models.Model):
    name = models.CharField(max_length=100, unique=True)
    building = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Computer(models.Model):
    CONDITIONS = [
        ("working", "Working"),
        ("under_repair", "Under Repair"),
        ("retired", "Retired"),
    ]
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    property_no = models.CharField(max_length=50, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    condition_status = models.CharField(max_length=20, choices=CONDITIONS, default="working")

    class Meta:
        ordering = ["property_no"]

    def __str__(self):
        return f"{self.property_no} - {self.location.name}"


class IssueCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "issue categories"

    def __str__(self):
        return self.name


class MaintenanceRequest(models.Model):
    PRIORITY = [("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")]
    STATUS = [
        ("pending", "Pending"),
        ("rejected", "Rejected"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("closed", "Closed"),
    ]
    STATUS_BADGE = {
        "pending": "warning text-dark", "rejected": "danger", "assigned": "info text-dark",
        "in_progress": "primary", "on_hold": "secondary", "completed": "success", "closed": "dark",
    }
    PRIORITY_BADGE = {"low": "secondary", "normal": "info text-dark", "high": "warning text-dark", "urgent": "danger"}

    ticket_no = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="requests")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs")
    computer = models.ForeignKey(Computer, on_delete=models.PROTECT)
    category = models.ForeignKey(IssueCategory, on_delete=models.PROTECT)
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=12, choices=PRIORITY, default="normal")
    status = models.CharField(max_length=15, choices=STATUS, default="pending")
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.ticket_no:
            self.ticket_no = f"CMR-{self.pk:04d}"
            super().save(update_fields=["ticket_no"])

    @property
    def status_badge(self):
        return self.STATUS_BADGE.get(self.status, "secondary")

    @property
    def priority_badge(self):
        return self.PRIORITY_BADGE.get(self.priority, "secondary")

    def __str__(self):
        return f"{self.ticket_no} - {self.title}"


class RequestUpdate(models.Model):
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name="updates")
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT)
    old_status = models.CharField(max_length=15, blank=True)
    new_status = models.CharField(max_length=15)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# ---- small helpers used by the views ----
def notify(users, message, req=None):
    if isinstance(users, User):
        users = [users]
    for u in users:
        Notification.objects.create(user=u, request=req, message=message[:255])


def add_history(req, user, old, new, remarks=""):
    RequestUpdate.objects.create(request=req, updated_by=user, old_status=old, new_status=new, remarks=remarks)


def admins():
    return User.objects.filter(role="admin", is_active=True)
