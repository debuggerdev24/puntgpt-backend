from django.db import models
from accounts.models import User



class SavedSearch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    filters = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_saved_search')
        ]
        ordering =['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.user})"
    