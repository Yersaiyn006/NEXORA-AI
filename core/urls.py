
from django.urls import path
from django.contrib.auth.views import LogoutView

from . import views, connect_views, launch_views
from .auth_views import BusinessLoginView
from .registration import register_business


urlpatterns = [
    path(
        "accounts/login/",
        BusinessLoginView.as_view(),
        name="login",
    ),
    path(
        "accounts/logout/",
        LogoutView.as_view(),
        name="logout",
    ),
    path(
        "accounts/register/",
        register_business,
        name="register",
    ),

    path(
        "launch/",
        launch_views.launch_home,
        name="launch_home",
    ),
    path(
        "launch/create/",
        launch_views.create_invite,
        name="launch_create",
    ),
    path(
        "launch/invite/<str:token>/",
        launch_views.accept_invite,
        name="launch_accept",
    ),
    path(
        "launch/<int:business_id>/setup/",
        launch_views.setup,
        name="launch_setup",
    ),
    path(
        "launch/<int:business_id>/catalog/",
        launch_views.catalog,
        name="launch_catalog",
    ),
    path(
        "launch/<int:business_id>/publish/",
        launch_views.publish,
        name="launch_publish",
    ),
    path(
        "launch/<int:business_id>/ready/",
        launch_views.ready,
        name="launch_ready",
    ),

    path(
        "connect/",
        connect_views.connect_home,
        name="connect_home",
    ),
    path(
        "connect/toggle/",
        connect_views.connect_toggle,
        name="connect_toggle",
    ),
    path(
        "connect/qr/",
        connect_views.connect_qr,
        name="connect_qr",
    ),

    path(
        "radar/",
        views.radar,
        name="radar",
    ),
    path(
        "",
        views.dashboard,
        name="dashboard",
    ),
    path(
        "leads/",
        views.leads,
        name="leads",
    ),
    path(
        "leads/<int:lead_id>/status/",
        views.lead_status,
        name="lead_status",
    ),
]
