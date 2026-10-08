from django.urls import path
from . import views

urlpatterns = [
    path("<slug:slug>/", views.chat_page, name="public_chat_page"),
    path("<slug:slug>/send/", views.chat_send, name="public_chat_send"),
]
