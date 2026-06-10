from django.contrib import admin

from .models import Patient, Report, RiskAssessment, SNPRecord


@admin.register(SNPRecord)
class SNPRecordAdmin(admin.ModelAdmin):
    list_display = ("server_serial", "created_by", "uploaded_at", "status")
    list_filter = ("status", "created_by", "uploaded_at")
    search_fields = ("server_serial", "created_by__username")


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("name", "gender", "hospital_serial", "created_by", "created_at")
    list_filter = ("created_by", "gender")
    search_fields = ("name", "hospital_serial", "created_by__username")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("report_serial", "patient", "snp_record", "created_by", "created_at")
    list_filter = ("created_by", "created_at")
    search_fields = ("report_serial", "patient__name", "patient__hospital_serial", "created_by__username")


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ("snp_record", "overall_risk_score", "calculated_at")
    search_fields = ("snp_record__server_serial",)

# Register your models here.
