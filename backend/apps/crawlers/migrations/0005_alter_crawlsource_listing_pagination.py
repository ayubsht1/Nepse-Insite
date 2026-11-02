from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crawlers", "0004_configure_publisher_sources"),
    ]

    operations = [
        migrations.AlterField(
            model_name="crawlsource",
            name="listing_pagination",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Optional page selector: a query parameter name (page), a query "
                    "template (?page={page}), or a full URL template containing {page}."
                ),
                max_length=1024,
            ),
        ),
    ]
