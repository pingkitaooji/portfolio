from django.urls import path
from django.views.generic import TemplateView

from . import views


urlpatterns = [
    path("", TemplateView.as_view(template_name="primerqc/index.html"), name="primerqc_home"),
    path("api/demo/", views.demo, name="primerqc_demo"),
    path("api/predict/", views.predict, name="primerqc_predict"),
]
