from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("snp/", views.snp_records, name="snp_records"),
    path("snp/<int:pk>/delete/", views.delete_snp, name="delete_snp"),
    path("reports/", views.report_list, name="report_list"),
    path("reports/<int:pk>/delete/", views.delete_report_view, name="delete_report"),
    path("reports/<int:pk>/download/", views.download_report, name="download_report"),
    path("api/snp-upload/", views.snp_upload_api, name="snp_upload_api"),
]
