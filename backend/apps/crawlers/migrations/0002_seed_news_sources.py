from django.db import migrations


SOURCES = [
    ("Mero Lagani", "merolagani", "https://merolagani.com"),
    ("ShareSansar", "sharesansar", "https://www.sharesansar.com"),
    ("NEPSE Alpha", "nepsealpha", "https://nepsealpha.com"),
    ("Bizmandu", "bizmandu", "https://bizmandu.com"),
]


def create_sources(apps, schema_editor):
    CrawlSource = apps.get_model("crawlers", "CrawlSource")
    CrawlSource.objects.using(schema_editor.connection.alias).bulk_create(
        [
            CrawlSource(
                name=name,
                key=key,
                base_url=base_url,
                enabled=False,
                request_interval_seconds=10,
                max_articles_per_run=50,
            )
            for name, key, base_url in SOURCES
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [("crawlers", "0001_initial")]

    operations = [migrations.RunPython(create_sources, migrations.RunPython.noop)]
