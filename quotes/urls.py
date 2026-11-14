from django.urls import path
from . import views

urlpatterns = [
    path("quotes/", views.quotes),
    path("quotes/random/", views.random_quote),
    path("quotes/<int:pk>/", views.quote_detail),
    path("categories/", views.categories),
    path("categories/<int:pk>/", views.category_detail),
    path("categories/<int:category_id>/quotes/", views.related_quotes),
    path("tags/", views.tags),
    path("tags/<int:pk>/", views.tag_detail),
    path("tags/<int:tag_id>/quotes/", views.related_quotes),
]
