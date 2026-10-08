
from django.urls import path
from . import views

urlpatterns = [
    path("", views.playground, name="ai_playground"),
    path("send/", views.send_message, name="ai_send_message"),

    path(
        "conversations/",
        views.conversation_list,
        name="ai_conversations",
    ),
    path(
        "conversations/<uuid:conversation_id>/",
        views.conversation_detail,
        name="ai_conversation_detail",
    ),
    path(
        "conversations/<uuid:conversation_id>/delete/",
        views.conversation_delete,
        name="ai_conversation_delete",
    ),
]
