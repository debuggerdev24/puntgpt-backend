from django.db import models
from accounts.models import User
from horse_race.models.selection import Selection

class TipSlip(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tip_slips')
    selection = models.ForeignKey(Selection, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'selection'], name='unique_tip_slip')
        ]
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user} - {self.selection}"
