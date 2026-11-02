import re
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError


_RANGE_PATTERN = re.compile(r"^(?P<days>[1-9]\d*)d$")


def parse_date_range(request):
    range_value = request.query_params.get("range", "30d")
    match = _RANGE_PATTERN.fullmatch(range_value)
    if range_value == "1y":
        days = 365
    elif match:
        days = int(match.group("days"))
        if days > 3650:
            raise ValidationError({"range": "Range may not exceed 3650 days."})
    elif range_value == "all":
        days = None
    else:
        raise ValidationError(
            {"range": "Use a day range such as 30d, 1y, or all."}
        )

    today = timezone.localdate()
    start_default = today - timedelta(days=days) if days is not None else None
    start_value = request.query_params.get("from")
    end_value = request.query_params.get("to")
    try:
        start = (
            timezone.datetime.strptime(start_value, "%Y-%m-%d").date()
            if start_value
            else start_default
        )
        end = (
            timezone.datetime.strptime(end_value, "%Y-%m-%d").date()
            if end_value
            else today
        )
    except ValueError as exc:
        raise ValidationError({"date": "Dates must use YYYY-MM-DD format."}) from exc
    if start and end and start > end:
        raise ValidationError({"from": "Start date must not be after end date."})
    return start, end
