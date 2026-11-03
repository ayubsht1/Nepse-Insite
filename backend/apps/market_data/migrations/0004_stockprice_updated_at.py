from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("market_data", "0003_marketindexsnapshot_updated_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockprice",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]