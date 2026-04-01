from django.db import models

class HourlyAggregation(models.Model):
    location  = models.TextField()
    hour      = models.DateTimeField()
    date      = models.DateField()
    total_in  = models.IntegerField()
    total_out = models.IntegerField()
    net_flow  = models.IntegerField()
    occupancy = models.IntegerField()

    class Meta:
        db_table = "hourly_aggregations"
        managed  = False

class DailyAggregation(models.Model):
    location  = models.TextField()
    date      = models.DateField()
    total_in  = models.IntegerField()
    total_out = models.IntegerField()
    net_flow  = models.IntegerField()

    class Meta:
        db_table = "daily_aggregations"
        managed  = False
