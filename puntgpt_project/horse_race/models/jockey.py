from django.db import models

class Jockey(models.Model):
    # from the /horse-racing/v1/identifiers/meeting/{date} api
    jockey_id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255, db_index=True)

    # from the /horse-racing/v1/statistics/jockey/{jockeyId} api
    # Career summary
    last_win = models.DateField(null=True, blank=True)
    total_prize_money = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    average_prize_money = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)


    # from the /horse-racing/v1/field/meeting/{meetingId}
    state = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=50, blank=True)
    is_apprentice = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Jockeys"


class JockeyStatistic(models.Model):
    jockey = models.ForeignKey(Jockey, on_delete=models.CASCADE, related_name='statistics')

    CATEGORY_CHOICES = [
        ('barrier', 'Barrier (Last 12 Months)'),
        ('distance', 'Distance (Last 12 Months)'),
        ('field_size', 'Field Size (Last 12 Months)'),
        ('group_race', 'Group Race (Last 12 Months)'),
        ('track_condition', 'Track Condition (Last 12 Months)'),
        ('track', 'Track (Last 12 Months)'),
        ('trainer', 'With Trainer (Last 12 Months)'),
        ('period', 'Period'),  # 12Months, asFavourite, lastTen, season, night
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    value = models.CharField(max_length=100, db_index=True)  # "1 - 3", "Good", "Peter Moody", "12Months"

    # Optional links
    track = models.ForeignKey('Track', on_delete=models.SET_NULL, null=True, blank=True)
    trainer = models.ForeignKey('Trainer', on_delete=models.SET_NULL, null=True, blank=True)

    # Stats
    runs = models.PositiveIntegerField()
    wins = models.PositiveIntegerField()
    seconds = models.PositiveIntegerField()
    thirds = models.PositiveIntegerField()
    win_percentage = models.DecimalField(max_digits=6, decimal_places=3)   # 0.197
    place_percentage = models.DecimalField(max_digits=6, decimal_places=3)
    roi = models.DecimalField(max_digits=8, decimal_places=3)

    class Meta:
        unique_together = ('jockey', 'category', 'value', 'track', 'trainer')
        indexes = [
            models.Index(fields=['category', 'value']),
            models.Index(fields=['win_percentage']),
            models.Index(fields=['jockey', 'category']),
        ]

    def __str__(self):
        extra = ""
        if self.track:
            extra = f" ({self.track})"
        if self.trainer:
            extra = f" (w/ {self.trainer})"
        return f"{self.jockey.name} | {self.get_category_display()}: {self.value}{extra} → {self.wins}/{self.runs}"