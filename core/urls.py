from django.urls import path
from . import views

urlpatterns = [
    path("radar/", views.radar, name="radar"),
    path("", views.dashboard, name="dashboard"),
    path("leads/", views.leads, name="leads"),
    path("leads/<int:lead_id>/status/", views.lead_status, name="lead_status"),
]
