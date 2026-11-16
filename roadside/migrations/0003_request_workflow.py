from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("roadside", "0002_assistancerequest_city_assistancerequest_district_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="assistancerequest",
            name="progress_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="assistancerequest",
            name="accepted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assistancerequest",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assistancerequest",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="RequestRejection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rejections", to="roadside.provider")),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rejections", to="roadside.assistancerequest")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("request", "provider"), name="unique_rejection_per_provider"),
                ],
            },
        ),
    ]
