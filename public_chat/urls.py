
from django.urls import path
from . import views

urlpatterns = [
    path(
        "<str:slug>/",
        views.chat_page,
        name="public_chat_page"
    ),
    path(
        "<str:slug>/send/",
        views.chat_send,
        name="public_chat_send"
    ),
]
