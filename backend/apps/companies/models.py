from django.db import models


class Company(models.Model):
    symbol = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255, unique=True)
    aliases = models.JSONField(default=list, blank=True)
    sector = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["symbol"]
        indexes = [models.Index(fields=["is_active", "symbol"])]

    def __str__(self):
        return f"{self.symbol} - {self.name}"
