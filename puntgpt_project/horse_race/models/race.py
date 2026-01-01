from django.db import models
from horse_race.models.meeting import Meeting

class Race(models.Model):
    # from the /horse-racing/v1/identifiers/meeting/{date} api 
    raceId = models.IntegerField(primary_key=True)
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='races')
    number = models.IntegerField(null=True, blank=True)
    isAbandoned = models.BooleanField(default=False)
    stage = models.CharField(max_length=50, blank=True, null=True)

   
    # from /horse-racing/v1/field/meeting/{meetingId}
    name = models.CharField(max_length=300, blank=True, null=True)
 
    distance = models.PositiveIntegerField(null=True, blank=True)
    distance_units = models.CharField(max_length=50, blank=True)
    
    prize_money = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    start_type = models.CharField(max_length=20, blank=True, null=True)
    startTimeUtc = models.DateTimeField(null=True, blank=True)
    startTimeUtc_raw = models.CharField(max_length=100, blank=True, null=True)
    startTimeUtcAus = models.DateTimeField(null=True, blank=True)
    
    track_condition = models.CharField(max_length=20, blank=True, null=True)
    track_condition_rating = models.IntegerField(null=True, blank=True)
    track_type = models.CharField(max_length=20, blank=True)
    
    # Entry conditions
    entry_conditions = models.JSONField(max_length=500, blank=True, null=True, default=None)


    # /horse-racing/v1/form/race/{raceId} => Now we are using the result api with the meeting id
    # official_time = models.DurationField(null=True, blank=True)  # e.g., "1:16.42" as timedelta
    # last_600_time = models.DurationField(null=True, blank=True)  # Sectional time
    race_starters = models.PositiveSmallIntegerField(null=True, blank=True)  # Number of starters

    # Winners/placers (foreign keys to Selection for easy querying)
    winner = models.ForeignKey('Selection', on_delete=models.SET_NULL, null=True, blank=True, related_name='races_won')
    second = models.ForeignKey('Selection', on_delete=models.SET_NULL, null=True, blank=True, related_name='races_second')
    third = models.ForeignKey('Selection', on_delete=models.SET_NULL, null=True, blank=True, related_name='races_third')

    class Meta:
        unique_together = ('meeting', 'number')  # Safety

    def __str__(self):
        return f"R{self.number} {self.meeting.track.name} {self.meeting.date}"