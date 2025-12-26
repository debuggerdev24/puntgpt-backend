from django.db import models
from horse_race.models.race import *

class Horse(models.Model):

    # from the /horse-racing/v1/identifiers/meeting/{date} api 
    horse_id = models.BigIntegerField(primary_key=True)  # FormPro uses large IDs
    name = models.CharField(max_length=255, db_index=True)

    # from the /horse-racing/v1/statistics/horse/{horseId} api
    # Career summary
    last_win = models.DateField(null=True, blank=True)
    average_prize_money = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_prize_money = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # from the from /horse-racing/v1/field/meeting/{meetingId}
    # Horse details 
    colour = models.CharField(max_length=20, blank=True)
    sex = models.CharField(max_length=10, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    foal_date = models.DateField(null=True, blank=True)
    sire = models.CharField(max_length=100, blank=True)
    dam = models.CharField(max_length=100, blank=True)
    damsire = models.CharField(max_length=100, blank=True)
    breeder = models.CharField(max_length=200, blank=True)
    owners = models.TextField(blank=True)
    training_location = models.CharField(max_length=100, blank=True)

    # from the /horse-racing/v1/form/race/{raceId}
    last_10_starts = models.CharField(max_length=10, blank=True)  

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Horses"

# Category + Value
CATEGORY_CHOICES = [
    ('barrier', 'Barrier'),
    ('distance', 'Distance Range'),
    ('track', 'Track'),
    ('track_condition', 'Track Condition'),
    ('track_surface', 'Track Surface'),
    ('resuming', 'Resuming'),
    ('weight', 'Weight Carried'),
    ('direction', 'Direction'),
    ('field_size', 'Field Size'),
    ('group_race', 'Group Race'),
    ('period', 'Period'),  # 12Months, lastTen, season, asFavourite, night
]

class HorseStatistic(models.Model):

    # from the /horse-racing/v1/statistics/horse/{horseId} api
    horse = models.ForeignKey(Horse, on_delete=models.CASCADE, related_name='statistics')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    value = models.CharField(max_length=100, db_index=True) 

    # Only for track-specific stats
    track = models.ForeignKey('Track', on_delete=models.SET_NULL, null=True, blank=True)

    # Performance numbers
    runs = models.PositiveIntegerField()
    wins = models.PositiveIntegerField()
    seconds = models.PositiveIntegerField()
    thirds = models.PositiveIntegerField()
    win_percentage = models.DecimalField(max_digits=6, decimal_places=3)    # 0.197
    place_percentage = models.DecimalField(max_digits=6, decimal_places=3)  # 0.466
    roi = models.DecimalField(max_digits=8, decimal_places=3)               # -0.144

    class Meta:
        unique_together = ('horse', 'category', 'value', 'track')  # track can be null
        indexes = [
            models.Index(fields=['category', 'value']),
            models.Index(fields=['win_percentage']),
            models.Index(fields=['place_percentage']),
            models.Index(fields=['horse', 'category']),
        ]

    def __str__(self):
        track = f" ({self.track})" if self.track else ""
        return f"{self.horse.name} | {self.get_category_display()}: {self.value}{track} → {self.wins}/{self.runs}"
    

# # /horse-racing/v1/form/race/{raceId}
# class HorseRaceHistory(models.Model):
#     horse = models.ForeignKey(Horse, on_delete=models.CASCADE, related_name='race_history')
    
#     # django allows: "app_label.ModelName" for avoding the circular import
#     race = models.ForeignKey('horse_race.Race', on_delete=models.CASCADE)
#     selection = models.ForeignKey('horse_race.Selection', on_delete=models.CASCADE, null=True, blank=True)  # Link to that race's selection

#     # Key history fields (from Form API)
#     finish_position = models.PositiveSmallIntegerField(null=True, blank=True)  # e.g., 1 for win
#     margin = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
#     starting_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
#     in_running = models.JSONField(blank=True, default=list)  # Same as Selection.in_running_positions
#     is_trial = models.BooleanField(default=False)

#     class Meta:
#         unique_together = ('horse', 'race')
#         ordering = ['-race__meeting__date']  # Most recent first

#     def __str__(self):
#         return f"{self.horse.name} in {self.race} - Pos: {self.finish_position}"