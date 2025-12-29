from django.db import models
from horse_race.models.race import Race
from horse_race.models.horse import Horse
from horse_race.models.jockey import Jockey
from horse_race.models.trainer import Trainer

class Selection(models.Model):

    # from the /horse-racing/v1/identifiers/meeting/{date} api 
    selectionId = models.IntegerField(primary_key=True)
    race = models.ForeignKey(Race, on_delete=models.CASCADE, related_name='selections')
    horse = models.ForeignKey(Horse, on_delete=models.CASCADE)
    jockey = models.ForeignKey(Jockey, on_delete=models.CASCADE, null=True, blank=True)
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, null=True, blank=True)

    number = models.IntegerField(null=True, blank=True)       # Rug/barrier number
    barrier = models.IntegerField(null=True, blank=True)
    isScratched = models.BooleanField(default=False)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    isEmergency = models.BooleanField(default=False)

    # from /horse-racing/v1/field/meeting/{meetingId}
    claim = models.IntegerField(null=True, blank=True)
    handicap_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    
    gear = models.TextField(blank=True)
    gear_changes = models.TextField(blank=True)
    
    racing_colours = models.CharField(max_length=255, blank=True)
    silks_image = models.URLField(blank=True)

    # /horse-racing/v1/form/race/{raceId}
    starting_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    result_position = models.PositiveSmallIntegerField(null=True, blank=True)  # e.g., 1 for win, 2 for place
    result_label = models.CharField(max_length=20, blank=True)  # e.g., "WON", "2ND", "UNPL"
    margin_decimal = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)  # Beaten margin
    weight_carried = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Actual weight carried
    in_running_positions = models.JSONField(blank=True, default=list)  # e.g., [{"distance": 600, "position": 1}]

    class Meta:
        unique_together = ('race', 'number')

    def __str__(self):
        return f"#{self.number} {self.horse.name} ({self.race})"