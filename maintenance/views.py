from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (CategoryForm, ComputerForm, LocationForm, RequestForm, ReviewForm,
                    TechUpdateForm, UserForm)
from .models import (Computer, IssueCategory, Location, MaintenanceRequest, Notification, User,
                     add_history, admins, notify)


# ------------------------------------------------------------------ helpers
def role_required(*roles):
    def deco(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                messages.error(request, "You do not have access to that page.")
                return redirect("dashboard")
            return view(request, *args, **kwargs)
        return wrapper
    return deco


def visible_requests(user):
    qs = MaintenanceRequest.objects.select_related(
        "requested_by", "assigned_to", "computer__location", "category")
    if user.role == "admin":
        return qs
    if user.role == "technician":
        return qs.filter(assigned_to=user)
    return qs.filter(requested_by=user)


# ---------------------------------------------------------------- dashboard
@login_required
def dashboard(request):
    qs = visible_requests(request.user)
    ctx = {
        "total": qs.count(),
        "pending": qs.filter(status="pending").count(),
        "active": qs.filter(status__in=["assigned", "in_progress", "on_hold"]).count(),
        "done": qs.filter(status__in=["completed", "closed"]).count(),
        "recent": qs[:6],
    }
    if request.user.role == "admin":
        ctx["to_review"] = qs.filter(status="pending")[:5]
        ctx["tech_count"] = User.objects.filter(role="technician", is_active=True).count()
        ctx["computer_count"] = Computer.objects.count()
    return render(request, "dashboard.html", ctx)


# ----------------------------------------------------------------- requests
@login_required
def request_list(request):
    qs = visible_requests(request.user)
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(ticket_no__icontains=q) | Q(computer__property_no__icontains=q))
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    return render(request, "requests/index.html", {
        "page": page, "status": status, "q": q, "statuses": MaintenanceRequest.STATUS})


@role_required("requester", "admin")
def request_add(request):
    form = RequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        r = form.save(commit=False)
        r.requested_by = request.user
        r.status = "pending"
        r.save()
        add_history(r, request.user, "", "pending", "Request submitted")
        notify(admins(), f"New request {r.ticket_no} from {request.user}", r)
        messages.success(request, f"Request {r.ticket_no} was submitted.")
        return redirect("request_detail", pk=r.pk)
    return render(request, "requests/add.html", {"form": form})


@login_required
def request_detail(request, pk):
    r = get_object_or_404(visible_requests(request.user), pk=pk)
    return render(request, "requests/detail.html", {
        "r": r, "updates": r.updates.select_related("updated_by")})


@role_required("requester", "admin")
def request_edit(request, pk):
    r = get_object_or_404(MaintenanceRequest, pk=pk, requested_by=request.user)
    if r.status not in ("pending", "rejected"):
        messages.error(request, "Only pending or rejected requests can be edited.")
        return redirect("request_detail", pk=r.pk)
    form = RequestForm(request.POST or None, instance=r)
    if request.method == "POST" and form.is_valid():
        old = r.status
        r = form.save(commit=False)
        r.status = "pending"
        r.save()
        if old == "rejected":
            add_history(r, request.user, old, "pending", "Edited and resubmitted")
            notify(admins(), f"Request {r.ticket_no} was edited and resubmitted", r)
        else:
            add_history(r, request.user, old, "pending", "Request edited")
        messages.success(request, "Request updated.")
        return redirect("request_detail", pk=r.pk)
    return render(request, "requests/edit.html", {"form": form, "r": r})


@login_required
def request_delete(request, pk):
    if request.user.role == "admin":
        r = get_object_or_404(MaintenanceRequest, pk=pk)
    else:
        r = get_object_or_404(MaintenanceRequest, pk=pk, requested_by=request.user, status="pending")
    if request.method == "POST":
        ticket = r.ticket_no
        r.delete()
        messages.success(request, f"Request {ticket} was deleted.")
        return redirect("request_list")
    return render(request, "requests/delete.html", {"r": r})


@role_required("admin")
def request_review(request, pk):
    r = get_object_or_404(MaintenanceRequest, pk=pk)
    if r.status != "pending":
        messages.error(request, "Only pending requests can be reviewed.")
        return redirect("request_detail", pk=r.pk)
    old = r.status
    form = ReviewForm(request.POST or None, instance=r)
    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action")
        r = form.save(commit=False)
        if action == "approve":
            if not r.assigned_to:
                form.add_error("assigned_to", "Choose a technician to approve this request.")
                return render(request, "requests/review.html", {"form": form, "r": r})
            r.status = "assigned"
            r.assigned_at = timezone.now()
            r.save()
            add_history(r, request.user, old, "assigned", f"Assigned to {r.assigned_to}. {r.review_note}".strip())
            notify(r.assigned_to, f"You were assigned request {r.ticket_no} ({r.get_priority_display()} priority)", r)
            notify(r.requested_by, f"Request {r.ticket_no} was approved and assigned to {r.assigned_to}", r)
            messages.success(request, "Request approved and assigned.")
        else:
            if not r.review_note:
                form.add_error("review_note", "Please give a reason for rejecting the request.")
                return render(request, "requests/review.html", {"form": form, "r": r})
            r.status = "rejected"
            r.assigned_to = None
            r.save()
            add_history(r, request.user, old, "rejected", r.review_note)
            notify(r.requested_by, f"Request {r.ticket_no} was rejected: {r.review_note}", r)
            messages.warning(request, "Request rejected.")
        return redirect("request_detail", pk=r.pk)
    return render(request, "requests/review.html", {"form": form, "r": r})


@role_required("technician")
def request_update(request, pk):
    r = get_object_or_404(MaintenanceRequest, pk=pk, assigned_to=request.user)
    if r.status not in ("assigned", "in_progress", "on_hold"):
        messages.error(request, "This request can no longer be updated.")
        return redirect("request_detail", pk=r.pk)
    initial = {"status": r.status if r.status != "assigned" else "in_progress"}
    form = TechUpdateForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        old = r.status
        new = form.cleaned_data["status"]
        remarks = form.cleaned_data["remarks"]
        r.status = new
        if new == "completed":
            r.completed_at = timezone.now()
            r.computer.condition_status = "working"
        else:
            r.computer.condition_status = "under_repair"
        r.computer.save()
        r.save()
        add_history(r, request.user, old, new, remarks)
        if new == "completed":
            notify(r.requested_by, f"Request {r.ticket_no} is completed. Please confirm the repair.", r)
            notify(admins(), f"Request {r.ticket_no} was marked completed by {request.user}", r)
        else:
            notify(r.requested_by, f"Request {r.ticket_no} is now {r.get_status_display()}", r)
        messages.success(request, "Status updated.")
        return redirect("request_detail", pk=r.pk)
    return render(request, "requests/update.html", {"form": form, "r": r})


@role_required("requester", "admin")
def request_confirm(request, pk):
    r = get_object_or_404(MaintenanceRequest, pk=pk, requested_by=request.user, status="completed")
    if request.method == "POST":
        remarks = request.POST.get("remarks", "").strip()
        if request.POST.get("action") == "confirm":
            r.status = "closed"
            r.save()
            add_history(r, request.user, "completed", "closed", remarks or "Repair confirmed by requester")
            if r.assigned_to:
                notify(r.assigned_to, f"Request {r.ticket_no} was confirmed and closed", r)
            messages.success(request, "Thank you. The request is now closed.")
        else:
            r.status = "in_progress"
            r.completed_at = None
            r.save()
            add_history(r, request.user, "completed", "in_progress", remarks or "Problem not fixed")
            if r.assigned_to:
                notify(r.assigned_to, f"Request {r.ticket_no} was sent back: problem not fixed", r)
            messages.warning(request, "The request was sent back to the technician.")
    return redirect("request_detail", pk=r.pk)


# ------------------------------------------------------------ notifications
@login_required
def notification_list(request):
    items = list(request.user.notifications.select_related("request")[:50])
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, "notifications.html", {"items": items})


# ------------------------------------------------------------------ reports
@role_required("admin")
def reports(request):
    by_status = [(label, MaintenanceRequest.objects.filter(status=key).count())
                 for key, label in MaintenanceRequest.STATUS]
    by_category = IssueCategory.objects.annotate(n=Count("maintenancerequest")).order_by("-n")
    by_location = Location.objects.annotate(n=Count("computer__maintenancerequest")).order_by("-n")
    by_tech = User.objects.filter(role="technician").annotate(n=Count("jobs")).order_by("-n")
    return render(request, "reports.html", {
        "by_status": by_status, "by_category": by_category,
        "by_location": by_location, "by_tech": by_tech})


# --------------------------------------------- admin CRUD (one set of views)
CRUD = {
    "users": {
        "model": User, "form": UserForm, "title": "Users",
        "cols": [("Username", "username"), ("Name", "get_full_name"), ("Role", "get_role_display"),
                 ("Department", "department"), ("Active", "is_active")],
    },
    "locations": {
        "model": Location, "form": LocationForm, "title": "Locations",
        "cols": [("Name", "name"), ("Building", "building"), ("Description", "description")],
    },
    "computers": {
        "model": Computer, "form": ComputerForm, "title": "Computers",
        "cols": [("Property No.", "property_no"), ("Location", "location"), ("Brand", "brand"),
                 ("Model", "model"), ("Condition", "get_condition_status_display")],
    },
    "categories": {
        "model": IssueCategory, "form": CategoryForm, "title": "Issue Categories",
        "cols": [("Name", "name"), ("Description", "description")],
    },
}


def _cfg(key):
    if key not in CRUD:
        from django.http import Http404
        raise Http404("Unknown record type")
    return CRUD[key]


def _cell(obj, attr):
    v = getattr(obj, attr)
    if callable(v):
        v = v()
    if v is True:
        return "Yes"
    if v is False:
        return "No"
    return v


@role_required("admin")
def crud_index(request, key):
    cfg = _cfg(key)
    objs = cfg["model"].objects.all()
    q = request.GET.get("q", "").strip()
    if q:
        first = cfg["cols"][0][1]
        objs = objs.filter(**{f"{first}__icontains": q})
    rows = [(o, [_cell(o, attr) for _, attr in cfg["cols"]]) for o in objs]
    return render(request, "crud/index.html", {
        "key": key, "title": cfg["title"], "headers": [h for h, _ in cfg["cols"]], "rows": rows, "q": q})


@role_required("admin")
def crud_add(request, key):
    cfg = _cfg(key)
    form = cfg["form"](request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{cfg['title']}: record added.")
        return redirect("crud_index", key=key)
    return render(request, "crud/add.html", {"key": key, "title": cfg["title"], "form": form})


@role_required("admin")
def crud_edit(request, key, pk):
    cfg = _cfg(key)
    obj = get_object_or_404(cfg["model"], pk=pk)
    form = cfg["form"](request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{cfg['title']}: record updated.")
        return redirect("crud_index", key=key)
    return render(request, "crud/edit.html", {"key": key, "title": cfg["title"], "form": form, "obj": obj})


@role_required("admin")
def crud_delete(request, key, pk):
    cfg = _cfg(key)
    obj = get_object_or_404(cfg["model"], pk=pk)
    if request.method == "POST":
        if key == "users" and obj.pk == request.user.pk:
            messages.error(request, "You cannot delete your own account.")
            return redirect("crud_index", key=key)
        try:
            obj.delete()
            messages.success(request, "Record deleted.")
        except ProtectedError:
            messages.error(request, "This record is used by other records (for example requests), so it cannot be deleted. "
                                    "For a user, you can untick Active instead.")
        return redirect("crud_index", key=key)
    return render(request, "crud/delete.html", {"key": key, "title": cfg["title"], "obj": obj})
