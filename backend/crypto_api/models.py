from django.db import models

class UpcomingCrypto(models.Model):
    project_name = models.CharField(max_length=200)
    project_symbol = models.CharField(max_length=20)
    project_url = models.URLField()
    project_type = models.CharField(max_length=50, null=True, blank=True)
    initial_cap = models.CharField(max_length=100, null=True, blank=True)
    ido_raise = models.CharField(max_length=100, null=True, blank=True)
    launch_date = models.DateField(null=True, blank=True)
    launch_date_original = models.CharField(max_length=50, null=True, blank=True)
    moni_score = models.CharField(max_length=10, null=True, blank=True)
    investors = models.JSONField(default=list)
    launchpad = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    parsed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cryptorank_upcoming'
        managed = True

class UpcomingSoon(models.Model):
    project_name = models.CharField(max_length=200)
    project_symbol = models.CharField(max_length=20)
    launch_date = models.DateField()
    days_until_launch = models.FloatField()

    class Meta:
        db_table = 'upcoming_soon'
        managed = False