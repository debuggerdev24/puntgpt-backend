from django.db import models

'''
 There are 6 predefined presets for the predictor model. so in order to avoid the user to create the preset
 I have craeted a json file in utils folder(preset.json) and run the code like this
 python manage.py loaddata "horse_race/utils/preset.json"
'''
class PredictorPreset(models.Model):
    preset_id = models.PositiveSmallIntegerField(primary_key=True)
    name = models.CharField(max_length=20, unique=True)  # BALANCED, WET_TRACK, etc.

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Predictor Presets"


# 2. One rating row per horse per preset
class PredictorRating(models.Model):
    selection = models.ForeignKey(
        'Selection',                     
        on_delete=models.CASCADE,
        related_name='predictor_ratings'
    )
    preset = models.ForeignKey(PredictorPreset, on_delete=models.CASCADE)

    normalised_rating = models.DecimalField(
        max_digits=6, decimal_places=5, db_index=True
    )  # e.g. 0.93421

    # rating_100 = models.PositiveSmallIntegerField(
    #     db_index=True
    # )  # e.g. 93 → for super-fast sorting

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('selection', 'preset')
        # indexes = [
        #     models.Index(fields=['rating_100']),
        #     models.Index(fields=['preset', 'rating_100']),
        # ]

    def __str__(self):
        return f"#{self.selection.number} {self.selection.horse.name} — {self.preset}"