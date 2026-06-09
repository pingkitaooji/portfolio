from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from .report_content import DISCLAIMER
from .models import Patient, Report, RiskAssessment, SNPRecord


SNP_CONTENT = (
    b"rsid,chromosome,position,genotype\n"
    b"PC,control,0,PASS\n"
    b"NC,control,0,PASS\n"
    b"rs1333049,9,22125503,GG\n"
    b"rs7903146,10,114758349,CT\n"
    b"rs4244285,10,96541616,AG\n"
)


class ReportWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="clinic_admin",
            password="demo123",
        )

    def test_machine_api_assigns_server_serial_checks_file_and_calculates_risk(self):
        upload = SimpleUploadedFile("sample_snp.csv", SNP_CONTENT, content_type="text/csv")

        response = self.client.post(
            reverse("snp_upload_api"),
            {
                "machine_serial": "MC-TEST-0001",
                "data_file": upload,
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["server_serial"].startswith("SNP-SRV-"))
        self.assertEqual(payload["snp_count"], 3)
        self.assertTrue(payload["pc_check_passed"])
        self.assertTrue(payload["nc_check_passed"])
        self.assertIn("overall_risk_score", payload)
        self.assertEqual(len(payload["risk_results"]), 3)
        snp = SNPRecord.objects.get(server_serial=payload["server_serial"])
        self.assertTrue(RiskAssessment.objects.filter(snp_record=snp).exists())

    def test_demo_snp_button_creates_record_and_risk_result(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("snp_records"), {"action": "generate_demo"})

        self.assertEqual(response.status_code, 302)
        snp = SNPRecord.objects.get()
        self.assertTrue(snp.server_serial.startswith("SNP-SRV-"))
        self.assertGreater(snp.snp_count, 0)
        self.assertTrue(snp.pc_check_passed)
        self.assertTrue(snp.nc_check_passed)
        self.assertEqual(snp.created_by, self.user)
        self.assertTrue(RiskAssessment.objects.filter(snp_record=snp).exists())

    def test_demo_snp_button_creates_random_file_content(self):
        self.client.force_login(self.user)

        self.client.post(reverse("snp_records"), {"action": "generate_demo"})
        first = SNPRecord.objects.get()
        first_content = first.data_file.read()

        self.client.post(reverse("snp_records"), {"action": "generate_demo"})
        second = SNPRecord.objects.exclude(pk=first.pk).get()
        second_content = second.data_file.read()

        self.assertNotEqual(first.machine_serial, second.machine_serial)
        self.assertNotEqual(first_content, second_content)

    def test_snp_page_shows_file_content_risk_and_patient_form(self):
        self.client.force_login(self.user)
        upload = SimpleUploadedFile("sample_snp.csv", SNP_CONTENT, content_type="text/csv")

        self.client.post(
            reverse("snp_records"),
            {
                "machine_serial": "MC-TEST-0002",
                "data_file": upload,
            },
        )
        snp = SNPRecord.objects.get(machine_serial="MC-TEST-0002")
        response = self.client.get(f"{reverse('snp_records')}?selected={snp.pk}")

        self.assertContains(response, "解析出的 SNP")
        self.assertContains(response, "rs1333049")
        self.assertContains(response, "SNP 風險結果")
        self.assertContains(response, "病人建檔")
        self.assertContains(response, "刪除")

    def test_snp_page_creates_report_from_selected_snp(self):
        self.client.force_login(self.user)
        self.client.post(reverse("snp_records"), {"action": "generate_demo"})
        snp = SNPRecord.objects.get()

        response = self.client.post(
            reverse("snp_records"),
            {
                "action": "create_report",
                "patient_name": "王小明",
                "gender": "male",
                "hospital_serial": "HSP-TEST-0001",
                "snp_record": snp.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Patient.objects.count(), 1)
        report = Report.objects.get()
        self.assertTrue(report.pdf_file.storage.exists(report.pdf_file.name))
        self.assertEqual(report.created_by, self.user)
        self.assertEqual(report.patient.created_by, self.user)
        self.assertEqual(report.risk_summary, snp.risk_assessment.risk_results)
        self.assertEqual(len(report.medical_advice), 3)
        self.assertEqual(report.disclaimer, DISCLAIMER)

    def test_delete_snp_without_report(self):
        self.client.force_login(self.user)
        self.client.post(reverse("snp_records"), {"action": "generate_demo"})
        snp = SNPRecord.objects.get()

        response = self.client.get(reverse("delete_snp", args=[snp.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(SNPRecord.objects.exists())

    def test_report_list_previews_and_deletes_selected_report(self):
        self.client.force_login(self.user)
        self.client.post(reverse("snp_records"), {"action": "generate_demo"})
        snp = SNPRecord.objects.get()
        self.client.post(
            reverse("snp_records"),
            {
                "action": "create_report",
                "patient_name": "王小明",
                "gender": "male",
                "hospital_serial": "HSP-TEST-0002",
                "snp_record": snp.pk,
            },
        )
        report = Report.objects.get()

        response = self.client.get(f"{reverse('report_list')}?selected={report.pk}")
        self.assertContains(response, "報告內容預覽")
        self.assertContains(response, report.report_serial)
        self.assertContains(response, "王小明")
        self.assertContains(response, "固定醫療建議")
        self.assertContains(response, "免責聲明")
        self.assertContains(response, "刪除")

        response = self.client.get(reverse("delete_report", args=[report.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Report.objects.exists())
        snp.refresh_from_db()
        self.assertEqual(snp.status, "ready")

    def test_patient_create_route_removed_and_sidebar_has_three_pages(self):
        self.client.force_login(self.user)
        with self.assertRaises(NoReverseMatch):
            reverse("patient_create")

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "總覽")
        self.assertContains(response, "SNP 資料")
        self.assertContains(response, "報告列表")
        self.assertNotContains(response, "病人建檔</a>")

    def test_hospital_users_only_see_their_own_snp_records(self):
        other_user = get_user_model().objects.create_user(
            username="hospital_b",
            password="demo123",
        )
        operator = get_user_model().objects.create_user(
            username="operator",
            password="demo123",
            is_staff=True,
        )

        self.client.force_login(self.user)
        self.client.post(reverse("snp_records"), {"action": "generate_demo"})
        own_snp = SNPRecord.objects.get(created_by=self.user)

        self.client.force_login(other_user)
        self.client.post(reverse("snp_records"), {"action": "generate_demo"})
        other_snp = SNPRecord.objects.get(created_by=other_user)

        self.client.get(reverse("dashboard"))
        response = self.client.get(reverse("snp_records"))
        self.assertContains(response, other_snp.server_serial)
        self.assertNotContains(response, own_snp.server_serial)

        response = self.client.get(f"{reverse('snp_records')}?selected={own_snp.pk}")
        self.assertEqual(response.status_code, 404)

        self.client.force_login(operator)
        response = self.client.get(reverse("snp_records"))
        self.assertContains(response, own_snp.server_serial)
        self.assertContains(response, other_snp.server_serial)

    def test_hospital_user_cannot_delete_or_download_other_users_report(self):
        other_user = get_user_model().objects.create_user(
            username="hospital_b",
            password="demo123",
        )
        self.client.force_login(self.user)
        self.client.post(reverse("snp_records"), {"action": "generate_demo"})
        snp = SNPRecord.objects.get(created_by=self.user)
        self.client.post(
            reverse("snp_records"),
            {
                "action": "create_report",
                "patient_name": "王小明",
                "gender": "male",
                "hospital_serial": "HSP-TEST-OWNED",
                "snp_record": snp.pk,
            },
        )
        report = Report.objects.get(created_by=self.user)

        self.client.force_login(other_user)
        self.assertEqual(self.client.get(reverse("download_report", args=[report.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("delete_report", args=[report.pk])).status_code, 404)
        self.assertTrue(Report.objects.filter(pk=report.pk).exists())

    def test_staff_user_can_see_record_creators(self):
        staff_user = get_user_model().objects.create_user(
            username="operator",
            password="demo123",
            is_staff=True,
        )
        self.client.force_login(self.user)
        self.client.post(reverse("snp_records"), {"action": "generate_demo"})
        snp = SNPRecord.objects.get(created_by=self.user)
        self.client.post(
            reverse("snp_records"),
            {
                "action": "create_report",
                "patient_name": "王小明",
                "gender": "male",
                "hospital_serial": "HSP-CREATOR-TEST",
                "snp_record": snp.pk,
            },
        )
        report = Report.objects.get(created_by=self.user)

        self.client.force_login(staff_user)
        response = self.client.get(reverse("snp_records"))
        self.assertContains(response, "建立者")
        self.assertContains(response, self.user.username)

        response = self.client.get(f"{reverse('report_list')}?selected={report.pk}")
        self.assertContains(response, "建立者")
        self.assertContains(response, self.user.username)

        self.client.force_login(self.user)
        response = self.client.get(reverse("snp_records"))
        self.assertNotContains(response, "建立者")

    def test_login_success_and_failure_are_logged(self):
        with self.assertLogs("reports.auth", level="INFO") as success_logs:
            response = self.client.post(
                reverse("login"),
                {"username": "clinic_admin", "password": "demo123"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("LOGIN_SUCCESS username=clinic_admin", "\n".join(success_logs.output))

        self.client.logout()
        with self.assertLogs("reports.auth", level="WARNING") as failed_logs:
            response = self.client.post(
                reverse("login"),
                {"username": "clinic_admin", "password": "wrong-password"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("LOGIN_FAILED username=clinic_admin", "\n".join(failed_logs.output))

    def test_login_csrf_failure_is_logged(self):
        csrf_client = Client(enforce_csrf_checks=True)
        with self.assertLogs("reports.csrf", level="WARNING") as csrf_logs:
            response = csrf_client.post(
                reverse("login"),
                {"username": "clinic_admin", "password": "demo123"},
            )
        self.assertEqual(response.status_code, 403)
        self.assertIn("LOGIN_CSRF_FAILURE username=clinic_admin", "\n".join(csrf_logs.output))
