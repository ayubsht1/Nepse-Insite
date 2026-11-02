from django.db import migrations


SOURCE_CONFIG = {
    "merolagani": (
        "https://merolagani.com/",
        r"/NewsDetail\.aspx\?newsID=\d+",
    ),
    "sharesansar": (
        "https://www.sharesansar.com/",
        r"/newsdetail/",
    ),
    "bizmandu": (
        "https://bizmandu.com/content/category/market.html",
        r"/content/\d{14}\.html$",
    ),
}


def configure_blank_sources(apps, schema_editor):
    CrawlSource = apps.get_model("crawlers", "CrawlSource")
    database = schema_editor.connection.alias
    for key, (listing_url, article_url_pattern) in SOURCE_CONFIG.items():
        source = CrawlSource.objects.using(database).filter(key=key).first()
        if source is None:
            continue
        updates = []
        if not source.listing_url:
            source.listing_url = listing_url
            updates.append("listing_url")
        if not source.article_url_pattern:
            source.article_url_pattern = article_url_pattern
            updates.append("article_url_pattern")
        if updates:
            source.save(using=database, update_fields=updates)


class Migration(migrations.Migration):
    dependencies = [("crawlers", "0002_seed_news_sources")]

    operations = [
        migrations.RunPython(
            configure_blank_sources,
            migrations.RunPython.noop,
        )
    ]
