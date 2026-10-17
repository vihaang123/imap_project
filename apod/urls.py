from django.urls import path

from . import views

urlpatterns = [
    path("apod/uncached/", views.apod_uncached, name="apod-uncached"),
    path("apod/low-level/", views.apod_low_level, name="apod-low-level"),
    path("apod/page-cached/", views.apod_page_cached, name="apod-page-cached"),
    path("cache/invalidate/", views.invalidate, name="cache-invalidate"),
    path("cache/stats/", views.stats, name="cache-stats"),
    path("cache/stats/reset/", views.reset_stats, name="cache-stats-reset"),
    path("override/", views.set_override, name="override"),
]
