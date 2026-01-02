from django.db import models
from horse_race.models.horse import Horse
from horse_race.models.jockey import Jockey


class JockeyHorseStatistic(models.Model):
    horse = models.ForeignKey(Horse, on_delete=models.CASCADE)
    jockey = models.ForeignKey(Jockey, on_delete=models.CASCADE)

    runs = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    seconds = models.PositiveIntegerField(default=0)
    thirds = models.PositiveIntegerField(default=0)

    win_percentage = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    place_percentage = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    roi = models.DecimalField(max_digits=8, decimal_places=3, default=0)

    last_ten_starts = models.CharField(max_length=15, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('horse', 'jockey')
        indexes = [
            models.Index(fields=['horse', 'jockey']),
            models.Index(fields=['win_percentage']),
            models.Index(fields=['place_percentage']),
        ]
