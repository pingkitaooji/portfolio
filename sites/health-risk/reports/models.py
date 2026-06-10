from django.conf import settings
from django.db import models
from django.utils import timezone


class SNPRecord(models.Model):
    STATUS_CHOICES = [
        ("ready", "待處理"),
        ("used", "已建立報告"),
        ("error", "資料異常"),
    ]

    server_serial = models.CharField(
        "樣本流水號",
        max_length=40,
        unique=True,
        editable=False,
    )
    data_file = models.FileField("SNP 原始資料", upload_to="snp_data/%Y/%m/%d/")
    uploaded_at = models.DateTimeField("接收時間", auto_now_add=True)
    status = models.CharField("狀態", max_length=12, choices=STATUS_CHOICES, default="ready")
    snp_count = models.PositiveIntegerField("SNP 筆數", default=0)
    pc_check_passed = models.BooleanField("PC check", default=False)
    nc_check_passed = models.BooleanField("NC check", default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="建立者",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "SNP 資料"
        verbose_name_plural = "SNP 資料"

    def save(self, *args, **kwargs):
        # Assign a server-side serial number as soon as a machine upload is stored.
        if not self.server_serial:
            self.server_serial = next_snp_serial()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.server_serial


class Patient(models.Model):
    GENDER_CHOICES = [
        ("female", "女性"),
        ("male", "男性"),
        ("other", "其他 / 未揭露"),
    ]

    name = models.CharField("病人名稱", max_length=80)
    gender = models.CharField("性別", max_length=12, choices=GENDER_CHOICES)
    hospital_serial = models.CharField("醫院端流水號", max_length=60, unique=True)
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="建立者",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "病人"
        verbose_name_plural = "病人"

    def __str__(self):
        return f"{self.name} ({self.hospital_serial})"


class Report(models.Model):
    report_serial = models.CharField("報告編號", max_length=40, unique=True)
    patient = models.ForeignKey(Patient, verbose_name="病人", on_delete=models.PROTECT)
    snp_record = models.ForeignKey(SNPRecord, verbose_name="SNP 資料", on_delete=models.PROTECT)
    pdf_file = models.FileField("PDF 報告檔", upload_to="reports/pdf/%Y/%m/%d/")
    risk_summary = models.JSONField("風險摘要", default=list)
    medical_advice = models.JSONField("固定醫療建議", default=list)
    disclaimer = models.TextField("免責聲明", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="建立者",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField("產生時間", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "健康風險評估報告系統"
        verbose_name_plural = "健康風險評估報告系統"

    def __str__(self):
        return self.report_serial


class RiskAssessment(models.Model):
    snp_record = models.OneToOneField(
        SNPRecord,
        verbose_name="SNP 資料",
        related_name="risk_assessment",
        on_delete=models.CASCADE,
    )
    overall_risk_score = models.PositiveIntegerField("總風險分數", default=0)
    risk_results = models.JSONField("風險計算結果", default=list)
    calculated_at = models.DateTimeField("計算時間", auto_now=True)

    class Meta:
        ordering = ["-calculated_at"]
        verbose_name = "SNP 風險計算結果"
        verbose_name_plural = "SNP 風險計算結果"

    def __str__(self):
        return f"{self.snp_record.server_serial} risk {self.overall_risk_score}"


def next_snp_serial():
    # Daily serials keep demo uploads readable while staying unique in the database.
    today = timezone.localdate().strftime("%Y%m%d")
    prefix = f"SNP-SRV-{today}-"
    latest = SNPRecord.objects.filter(server_serial__startswith=prefix).order_by("-server_serial").first()
    if not latest:
        return f"{prefix}0001"

    next_number = int(latest.server_serial.rsplit("-", 1)[-1]) + 1
    return f"{prefix}{next_number:04d}"
