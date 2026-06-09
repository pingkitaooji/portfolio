from django.urls import path
from django.views.generic import TemplateView

from . import views


urlpatterns = [
    path("", TemplateView.as_view(template_name="cqcalling/index.html"), name="cqcalling_home"),
    path("api/analyze/", views.analyze, name="cqcalling_analyze"),
]
