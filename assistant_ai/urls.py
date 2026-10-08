from django.urls import path
from . import views

urlpatterns = [
    path("", views.playground, name="ai_playground"),
    path("send/", views.send_message, name="ai_send_message"),
]