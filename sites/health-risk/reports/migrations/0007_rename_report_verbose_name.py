from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0006_backfill_report_advice"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="report",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "健康風險評估報告系統",
                "verbose_name_plural": "健康風險評估報告系統",
            },
        ),
    ]
