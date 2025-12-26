from django.db import models

class Trainer(models.Model):
    trainer_id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255, db_index=True)

    last_win = models.DateField(null=True, blank=True)
    total_prize_money = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    average_prize_money = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # from /horse-racing/v1/field/meeting/{meetingId}
    location = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=10, blank=True)
    state = models.CharField(max_length=10, blank=True)
    title = models.CharField(max_length=10, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Trainers"


class TrainerStatistic(models.Model):
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='statistics')

    CATEGORY_CHOICES = [
        ('distance', 'Distance (Last 12 Months)'),
        ('group_race', 'Group Race (Last 12 Months)'),
        ('resuming', 'Resuming (Last 12 Months)'),
        ('track', 'Track (Last 12 Months)'),
        ('jockey', 'With Jockey (Last 12 Months)'),
        ('period', 'Period'),  # 12Months, lastTen, season, asFavourite, night
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    value = models.CharField(max_length=100, db_index=True)  # "First Up", "Luke Nolen", "1301 - 1500m"

    # Optional foreign keys
    track = models.ForeignKey('Track', on_delete=models.SET_NULL, null=True, blank=True)
    jockey = models.ForeignKey('Jockey', on_delete=models.SET_NULL, null=True, blank=True)

    # Stats
    runs = models.PositiveIntegerField()
    wins = models.PositiveIntegerField()
    seconds = models.PositiveIntegerField()
    thirds = models.PositiveIntegerField()
    win_percentage = models.DecimalField(max_digits=6, decimal_places=3)
    place_percentage = models.DecimalField(max_digits=6, decimal_places=3)
    roi = models.DecimalField(max_digits=8, decimal_places=3)

    class Meta:
        unique_together = ('trainer', 'category', 'value', 'track', 'jockey')
        indexes = [
            models.Index(fields=['category', 'value']),
            models.Index(fields=['win_percentage']),
            models.Index(fields=['trainer', 'category']),
        ]

    def __str__(self):
        extra = ""
        if self.track: extra = f" ({self.track})"
        if self.jockey: extra = f" (w/ {self.jockey})"
        return f"{self.trainer.name} | {self.get_category_display()}: {self.value}{extra} → {self.wins}/{self.runs}"