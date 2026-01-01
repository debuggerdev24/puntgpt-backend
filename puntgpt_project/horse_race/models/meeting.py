from django.db import models
from horse_race.models.track import Track

class Meeting(models.Model):
    # from the /horse-racing/v1/identifiers/meeting/{date} api 
    meetingId = models.IntegerField(primary_key=True)
    date = models.DateField(db_index=True)                    # Very useful index
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    isTrial = models.BooleanField(default=False)
    stage = models.CharField(max_length=50)                   # e.g. FinalFields, Results
    startTimeUtc = models.DateTimeField(null=True, blank=True)
    startTimeUtc_raw = models.CharField(max_length=100, null=True, blank=True)

    # from /horse-racing/v1/field/meeting/{meetingId}
    name = models.CharField(max_length=200, blank=True)           # "bet365 Bairnsdale"
    category = models.CharField(max_length=50, blank=True)        # Professional, Picnic
    meeting_type = models.CharField(max_length=20, blank=True, null=True)    # Metro, Provincial
    time_slot = models.CharField(max_length=20, blank=True)       # Morning, Twilight, Night
    rail_position = models.CharField(max_length=50, blank=True)
    weather_condition = models.CharField(max_length=50, blank=True)
    temperature = models.PositiveSmallIntegerField(null=True, blank=True)
    tab_status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.date} - {self.track.name}"