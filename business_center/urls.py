from django.urls import path
from . import views
urlpatterns = [
    path("", views.studio, name="business_studio"),
    path("knowledge/save/", views.knowledge_save, name="studio_knowledge_save"),
    path("knowledge/<int:item_id>/delete/", views.knowledge_delete, name="studio_knowledge_delete"),
    path("booking/<int:lead_id>/", views.booking_action, name="studio_booking_action"),
]
