from django.db import migrations, models


SOURCE_CONFIG = {
    "merolagani": {
        "base_url": "https://merolagani.com",
        "listing_url": "https://merolagani.com/NewsList.aspx",
        "listing_pagination": "",
        "article_url_pattern": (
            r"https://merolagani\.com/NewsDetail\.aspx\?newsID=\d+"
        ),
        "previous_listing_url": "https://merolagani.com/",
        "previous_article_url_pattern": r"/NewsDetail\.aspx\?newsID=\d+",
    },
    "sharesansar": {
        "base_url": "https://www.sharesansar.com",
        "listing_url": "https://www.sharesansar.com/news-page",
        "listing_pagination": "",
        "article_url_pattern": (
            r"https://www\.sharesansar\.com/(index\.php/)?newsdetail/[\w-]+"
        ),
        "previous_listing_url": "https://www.sharesansar.com/",
        "previous_article_url_pattern": r"/newsdetail/",
    },
    "bizmandu": {
        "base_url": "https://bizmandu.com",
        "listing_url": "https://bizmandu.com/content/category/news.html",
        "listing_pagination": "",
        "article_url_pattern": r"https://bizmandu\.com/content/\d+\.html",
        "previous_listing_url": "https://bizmandu.com/content/category/market.html",
        "previous_article_url_pattern": r"/content/\d{14}\.html$",
    },
    "nepsealpha": {
        "base_url": "https://www.nepsealpha.com",
        "listing_url": (
            "https://www.nepsealpha.com/all-news?cid=1&page=1"
        ),
        "listing_pagination": (
            "https://www.nepsealpha.com/all-news?cid=1&page={page}"
        ),
        "article_url_pattern": (
            r"https://(www\.)?nepsealpha\.com/news(-article|/article)/[\w-]+"
        ),
        "previous_listing_url": "",
        "previous_article_url_pattern": "",
    },
}


def configure_publisher_sources(apps, schema_editor):
    CrawlSource = apps.get_model("crawlers", "CrawlSource")
    database = schema_editor.connection.alias
    for key, config in SOURCE_CONFIG.items():
        source = CrawlSource.objects.using(database).filter(key=key).first()
        if source is None:
            continue

        updates = []
        if not source.base_url or source.base_url in {
            "https://merolagani.com",
            "https://www.sharesansar.com",
            "https://bizmandu.com",
            "https://nepsealpha.com",
        }:
            source.base_url = config["base_url"]
            updates.append("base_url")
        if (
            not source.listing_url
            or source.listing_url == config["previous_listing_url"]
        ):
            source.listing_url = config["listing_url"]
            updates.append("listing_url")
        if not source.listing_pagination:
            source.listing_pagination = config["listing_pagination"]
            updates.append("listing_pagination")
        if (
            not source.article_url_pattern
            or source.article_url_pattern == config["previous_article_url_pattern"]
        ):
            source.article_url_pattern = config["article_url_pattern"]
            updates.append("article_url_pattern")
        if updates:
            source.save(using=database, update_fields=updates)


class Migration(migrations.Migration):
    dependencies = [("crawlers", "0003_configure_verified_listing_pages")]

    operations = [
        migrations.AddField(
            model_name="crawlsource",
            name="listing_pagination",
            field=models.CharField(blank=True, max_length=1024),
        ),
        migrations.AddField(
            model_name="crawlsource",
            name="max_listing_pages",
            field=models.PositiveSmallIntegerField(default=10),
        ),
        migrations.RunPython(
            configure_publisher_sources,
            migrations.RunPython.noop,
        ),
    ]
