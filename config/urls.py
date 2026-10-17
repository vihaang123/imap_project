from django.contrib import admin
from django.urls import include, path

from apod import views as apod_views

urlpatterns = [
    path("", apod_views.dashboard, name="dashboard"),
    path("admin/", admin.site.urls),
    path("api/", include("apod.urls")),
]
