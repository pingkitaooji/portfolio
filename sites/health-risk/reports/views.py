from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import ProtectedError
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .demo_snp import create_demo_snp_record
from .forms import PatientReportForm, SNPUploadForm
from .models import Patient, Report, RiskAssessment, SNPRecord
from .pdf import create_sample_pdf
from .report_content import DISCLAIMER, build_medical_advice
from .risk_calculator import calculate_and_store_risk
from .snp_parser import inspect_snp_file, update_snp_checks


@login_required
def dashboard(request):
    snp_records = snp_queryset_for_user(request.user)
    reports = report_queryset_for_user(request.user)
    context = base_metrics(request.user)
    context.update(
        {
            "active_page": "dashboard",
            "page_kicker": "總覽",
            "page_title": "待處理工作總覽",
            "uploaded_snp_records": snp_records[:8],
            "pending_snp_records": snp_records.filter(status="ready")[:8],
            "recent_reports": reports.select_related("patient", "snp_record")[:6],
        }
    )
    return render(request, "reports/dashboard.html", context)


@login_required
def snp_records(request):
    # This page combines upload, demo data generation, SNP preview, and report creation.
    upload_form = SNPUploadForm()
    selected_id = request.GET.get("selected")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "generate_demo":
            snp_record = create_demo_snp_record(request.user)
            messages.success(request, f"DEMO SNP 已產生：{snp_record.server_serial}")
            return redirect(f"{reverse('snp_records')}?selected={snp_record.pk}")

        if action == "delete_snp":
            snp_record = get_object_or_404(snp_queryset_for_user(request.user), pk=request.POST.get("snp_id"))
            serial = snp_record.server_serial
            try:
                delete_snp_record(snp_record)
                messages.success(request, f"已刪除 SNP 檔案：{serial}")
            except ProtectedError:
                messages.error(request, "此 SNP 已被報告使用，請先刪除對應報告後再刪除 SNP。")
                return redirect(f"{reverse('snp_records')}?selected={snp_record.pk}")
            return redirect("snp_records")

        if action == "create_report":
            report_form = PatientReportForm(request.POST, user=request.user)
            if report_form.is_valid():
                report = create_report_from_form(report_form, request.user)
                messages.success(request, f"PDF 報告已產生並保存：{report.report_serial}")
                return redirect(f"{reverse('report_list')}?selected={report.pk}")
            messages.error(request, "報告建立失敗，請確認病人資料與 SNP 資料。")
            selected_id = request.POST.get("snp_record") or selected_id
        else:
            upload_form = SNPUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                snp_record = upload_form.save(commit=False)
                snp_record.created_by = request.user
                snp_record.save()
                update_snp_checks(snp_record)
                calculate_and_store_risk(snp_record)
                messages.success(request, f"SNP 資料已保存，系統給予統一流水號：{snp_record.server_serial}")
                return redirect(f"{reverse('snp_records')}?selected={snp_record.pk}")
            messages.error(request, "SNP 上傳失敗，請確認機台流水號與檔案已填寫。")

    snp_records_qs = snp_queryset_for_user(request.user)
    selected_record = selected_snp_record(selected_id, snp_records_qs)
    selected_inspection = inspect_snp_file(selected_record.data_file) if selected_record else None
    selected_risk = getattr(selected_record, "risk_assessment", None) if selected_record else None
    report_form = PatientReportForm(
        initial={"snp_record": selected_record.pk if selected_record else None},
        user=request.user,
    )

    context = base_metrics(request.user)
    context.update(
        {
            "active_page": "snp",
            "page_kicker": "SNP 資料",
            "page_title": "已上傳檔案與病人建檔",
            "upload_form": upload_form,
            "report_form": report_form,
            "snp_records": snp_records_qs[:50],
            "selected_snp": selected_record,
            "selected_inspection": selected_inspection,
            "selected_risk": selected_risk,
        }
    )
    return render(request, "reports/snp_records.html", context)


@login_required
def report_list(request):
    selected_id = request.GET.get("selected")
    if request.method == "POST" and request.POST.get("action") == "delete_report":
        report = get_object_or_404(report_queryset_for_user(request.user), pk=request.POST.get("report_id"))
        serial = report.report_serial
        delete_report(report)
        messages.success(request, f"已刪除報告：{serial}")
        return redirect("report_list")

    reports = report_queryset_for_user(request.user).select_related("patient", "snp_record")
    selected_report = selected_report_record(selected_id, reports)
    context = base_metrics(request.user)
    context.update(
        {
            "active_page": "reports",
            "page_kicker": "報告列表",
            "page_title": "已建立報告資料",
            "reports": reports[:50],
            "selected_report": selected_report,
        }
    )
    return render(request, "reports/report_list.html", context)


@login_required
def delete_snp(request, pk):
    snp_record = get_object_or_404(snp_queryset_for_user(request.user), pk=pk)
    serial = snp_record.server_serial
    try:
        delete_snp_record(snp_record)
        messages.success(request, f"已刪除 SNP 檔案：{serial}")
    except ProtectedError:
        messages.error(request, "此 SNP 已被報告使用，請先刪除對應報告後再刪除 SNP。")
        return redirect(f"{reverse('snp_records')}?selected={pk}")
    return redirect("snp_records")


@login_required
def delete_report_view(request, pk):
    report = get_object_or_404(report_queryset_for_user(request.user), pk=pk)
    serial = report.report_serial
    delete_report(report)
    messages.success(request, f"已刪除報告：{serial}")
    return redirect("report_list")


def user_can_view_all(user):
    return user.is_staff or user.is_superuser


def snp_queryset_for_user(user):
    queryset = SNPRecord.objects.all()
    if user_can_view_all(user):
        return queryset
    return queryset.filter(created_by=user)


def patient_queryset_for_user(user):
    queryset = Patient.objects.all()
    if user_can_view_all(user):
        return queryset
    return queryset.filter(created_by=user)


def report_queryset_for_user(user):
    queryset = Report.objects.all()
    if user_can_view_all(user):
        return queryset
    return queryset.filter(created_by=user)


def base_metrics(user):
    snp_records = snp_queryset_for_user(user)
    patients = patient_queryset_for_user(user)
    reports = report_queryset_for_user(user)
    return {
        "snp_count": snp_records.count(),
        "ready_count": snp_records.filter(status="ready").count(),
        "patient_count": patients.count(),
        "report_count": reports.count(),
        "pc_pass_count": snp_records.filter(pc_check_passed=True).count(),
        "nc_pass_count": snp_records.filter(nc_check_passed=True).count(),
        "risk_count": RiskAssessment.objects.filter(snp_record__in=snp_records).count(),
    }


def selected_snp_record(selected_id, records):
    if selected_id:
        return get_object_or_404(records, pk=selected_id)
    return records[0] if records else None


def selected_report_record(selected_id, reports):
    if selected_id:
        return get_object_or_404(reports.select_related("patient", "snp_record"), pk=selected_id)
    return reports[0] if reports else None


def create_report_from_form(form, user):
    # Keep patient creation, risk calculation, PDF creation, and status update atomic.
    with transaction.atomic():
        patient, _ = Patient.objects.update_or_create(
            hospital_serial=form.cleaned_data["hospital_serial"],
            defaults={
                "name": form.cleaned_data["patient_name"],
                "gender": form.cleaned_data["gender"],
                "created_by": user,
            },
        )
        snp_record = form.cleaned_data["snp_record"]
        report_serial = next_report_serial()
        assessment = getattr(snp_record, "risk_assessment", None) or calculate_and_store_risk(snp_record)
        risks = assessment.risk_results
        medical_advice = build_medical_advice(risks)
        pdf_bytes = create_sample_pdf(report_serial, patient, snp_record, risks, medical_advice, DISCLAIMER)

        report = Report(
            report_serial=report_serial,
            patient=patient,
            snp_record=snp_record,
            risk_summary=risks,
            medical_advice=medical_advice,
            disclaimer=DISCLAIMER,
            created_by=user,
        )
        report.pdf_file.save(f"{report_serial}.pdf", ContentFile(pdf_bytes), save=True)

        snp_record.status = "used"
        snp_record.save(update_fields=["status"])
        return report


def delete_snp_record(snp_record):
    file_name = snp_record.data_file.name
    storage = snp_record.data_file.storage
    snp_record.delete()
    if file_name and storage.exists(file_name):
        storage.delete(file_name)


def delete_report(report):
    file_name = report.pdf_file.name
    storage = report.pdf_file.storage
    snp_record = report.snp_record
    report.delete()
    if file_name and storage.exists(file_name):
        storage.delete(file_name)
    if not Report.objects.filter(snp_record=snp_record).exists():
        snp_record.status = "ready"
        snp_record.save(update_fields=["status"])


@login_required
def download_report(request, pk):
    report = get_object_or_404(report_queryset_for_user(request.user), pk=pk)
    return FileResponse(
        report.pdf_file.open("rb"),
        as_attachment=True,
        filename=f"{report.report_serial}.pdf",
        content_type="application/pdf",
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def snp_upload_api(request):
    # Simulates the instrument-facing upload endpoint used by automated SNP machines.
    if request.method == "GET":
        return JsonResponse(
            {
                "message": "POST machine_serial and data_file to upload SNP data. The server_serial is assigned after upload.",
                "required_fields": ["machine_serial", "data_file"],
                "assigned_field": "server_serial",
            }
        )

    form = SNPUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    snp_record = form.save()
    inspection = update_snp_checks(snp_record)
    assessment = calculate_and_store_risk(snp_record)
    return JsonResponse(
        {
            "ok": True,
            "server_serial": snp_record.server_serial,
            "machine_serial": snp_record.machine_serial,
            "uploaded_at": snp_record.uploaded_at.isoformat(),
            "snp_count": inspection["snp_count"],
            "pc_check_passed": inspection["pc_check_passed"],
            "nc_check_passed": inspection["nc_check_passed"],
            "overall_risk_score": assessment.overall_risk_score,
            "risk_results": assessment.risk_results,
        },
        status=201,
    )


def next_report_serial():
    today = timezone.localdate().strftime("%Y%m%d")
    prefix = f"RPT-{today}-"
    latest = Report.objects.filter(report_serial__startswith=prefix).order_by("-report_serial").first()
    if not latest:
        return f"{prefix}0001"

    next_number = int(latest.report_serial.rsplit("-", 1)[-1]) + 1
    return f"{prefix}{next_number:04d}"
