from django import forms

from .models import Patient, SNPRecord


class SNPUploadForm(forms.ModelForm):
    class Meta:
        model = SNPRecord
        fields = ["machine_serial", "data_file"]
        widgets = {
            "machine_serial": forms.TextInput(attrs={"placeholder": "例如：MC-8F2A-4410"}),
        }


class PatientReportForm(forms.Form):
    patient_name = forms.CharField(
        label="病人名稱",
        max_length=80,
        widget=forms.TextInput(attrs={"placeholder": "例如：王小明"}),
    )
    gender = forms.ChoiceField(label="性別", choices=Patient.GENDER_CHOICES)
    hospital_serial = forms.CharField(
        label="醫院端流水號",
        max_length=60,
        widget=forms.TextInput(attrs={"placeholder": "例如：HSP-20260531-001"}),
    )
    snp_record = forms.ModelChoiceField(
        label="對應 SNP 資料",
        queryset=SNPRecord.objects.none(),
        empty_label="請選擇伺服器流水號",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = SNPRecord.objects.filter(status="ready")
        if user and not (user.is_staff or user.is_superuser):
            queryset = queryset.filter(created_by=user)
        self.fields["snp_record"].queryset = queryset
