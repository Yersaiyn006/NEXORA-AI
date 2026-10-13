from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="brain_home"),
    path("profile/", views.save_profile, name="brain_profile"),
    path("item/save/", views.save_item, name="brain_item_save"),
    path("item/<int:item_id>/delete/", views.delete_item, name="brain_item_delete"),
]
