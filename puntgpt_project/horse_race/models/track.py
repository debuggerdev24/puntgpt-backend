from django.db import models

class Track(models.Model):
    # from the /horse-racing/v1/identifiers/meeting/{date} api 
    trackId = models.IntegerField(primary_key=True)        
    name = models.CharField(max_length=255)
    countryIso2 = models.CharField(max_length=2)

    # from /horse-racing/v1/field/meeting/{meetingId}
    address = models.CharField(max_length=255, blank=True)
    circumference = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    straight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    is_clockwise = models.BooleanField(null=True)
    sprint_lane = models.BooleanField(default=False)
    surface = models.CharField(max_length=20, blank=True)
    track_code = models.CharField(max_length=20, blank=True)
    
    class Meta:
        verbose_name_plural = "Track Details"
    

    def __str__(self):
        return f"{self.name} ({self.countryIso2})"