import re
from decimal import Decimal

from django.db import transaction

from apps.companies.models import Company
from apps.news.models import NewsArticle, NewsCompanyTag


def _contains_term(text, term):
    normalized_term = " ".join(term.split()).strip()
    if not normalized_term:
        return False
    pattern = rf"(?<!\w){re.escape(normalized_term)}(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


@transaction.atomic
def categorize_article(article: NewsArticle):
    text = f"{article.headline}\n{article.body}"
    tags = []
    companies = Company.objects.filter(is_active=True).only(
        "id", "name", "symbol", "aliases"
    )

    for company in companies:
        matches_symbol = _contains_term(text, company.symbol)
        matches_name = _contains_term(text, company.name)
        matches_alias = any(
            _contains_term(text, alias)
            for alias in company.aliases
            if isinstance(alias, str)
        )
        if not (matches_symbol or matches_name or matches_alias):
            continue

        confidence = (
            Decimal("0.980")
            if matches_symbol
            else Decimal("0.900")
            if matches_name
            else Decimal("0.800")
        )
        tag, created = NewsCompanyTag.objects.get_or_create(
            article=article,
            company=company,
            defaults={
                "confidence_score": confidence,
                "method": NewsCompanyTag.Method.RULE,
            },
        )
        if not created and tag.method == NewsCompanyTag.Method.RULE:
            tag.confidence_score = confidence
            tag.save(update_fields=["confidence_score", "updated_at"])
        tags.append(tag)
    return tags
