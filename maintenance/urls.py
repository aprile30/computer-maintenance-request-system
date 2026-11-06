from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import path

from . import views

urlpatterns = [
    path("", lambda request: redirect("dashboard")),
    path("login/", auth_views.LoginView.as_view(template_name="login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # maintenance requests
    path("requests/", views.request_list, name="request_list"),
    path("requests/add/", views.request_add, name="request_add"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/edit/", views.request_edit, name="request_edit"),
    path("requests/<int:pk>/delete/", views.request_delete, name="request_delete"),
    path("requests/<int:pk>/review/", views.request_review, name="request_review"),
    path("requests/<int:pk>/update/", views.request_update, name="request_update"),
    path("requests/<int:pk>/confirm/", views.request_confirm, name="request_confirm"),

    path("notifications/", views.notification_list, name="notifications"),
    path("reports/", views.reports, name="reports"),

    # admin CRUD: users, locations, computers, categories
    path("manage/<str:key>/", views.crud_index, name="crud_index"),
    path("manage/<str:key>/add/", views.crud_add, name="crud_add"),
    path("manage/<str:key>/<int:pk>/edit/", views.crud_edit, name="crud_edit"),
    path("manage/<str:key>/<int:pk>/delete/", views.crud_delete, name="crud_delete"),
]
