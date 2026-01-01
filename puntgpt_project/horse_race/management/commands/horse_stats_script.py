from django.core.management.base import BaseCommand
import requests
from datetime import datetime, timezone, time, date
from django.db import transaction
from django.conf import settings
from decimal import Decimal
from dateutil import parser
from django.utils import timezone as dj_timezone 


# Model importing:
from horse_race.models.horse import *
from horse_race.models.jockey import *
from horse_race.models.trainer import *
from horse_race.models.track import *
from horse_race.models.meeting import *
from horse_race.models.race import *
from horse_race.models.selection import *
from horse_race.models.predictor import *

BASE_URL = "https://api.formpro.com.au"

# 2.Advances statistics horse detail api
class Command(BaseCommand):
    def handle(self, *args, **options):

        # no need of refreshing all horses perday so we will fetch the data of the horse that participated in today race.
        target_date = date.today()
        if options.get('date'):
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()

        start_dt = dj_timezone.make_aware(datetime.combine(target_date, time.min), timezone=timezone.utc)
        end_dt   = dj_timezone.make_aware(datetime.combine(target_date, time.max), timezone=timezone.utc)

        print(start_dt, end_dt)
        horse_ids = (
            Selection.objects
            .filter(race__meeting__startTimeUtc__range=(start_dt, end_dt))
            .values_list('horse_id', flat=True)
            .distinct()
        )
        total = horse_ids.count()
        print(f"Total horses to sync: {total}")

        for horse_id in horse_ids:
            self.sync_horse_detail(horse_id)
        
        # for checking purpose:
        # horse = Horse.objects.first()
        # self.sync_horse_detail(horse.horse_id)
     
    def sync_horse_detail(self,horse_id: int):
        url = f"{BASE_URL}/horse-racing/v1/statistics/horse/{horse_id}"
        headers = {"Authorization": f"Bearer {settings.FORMPRO_API_KEY}"}
        try:
            req = requests.get(url, headers=headers)
            req.raise_for_status()
        except Exception as e:
            print(f"API error {e} for horse {horse_id}")
            return False
    
        data = req.json()

        if data:
            # Fetching the horse id
            horse_data = data["horse"]
            stats = data["horseStatistics"]

            with transaction.atomic():
                # Fetching the horse row
                horse_obj, created = Horse.objects.update_or_create(
                horse_id=horse_data["horseId"],
                defaults={
                    "name": horse_data["name"],
                    "last_win": stats.get("lastWin"),
                    "average_prize_money": stats.get("averagePrizeMoney"),
                    "total_prize_money": stats.get("totalPrizeMoney"),
                }
            )
                
                HorseStatistic.objects.filter(horse=horse_obj).delete()

                # updating the statistics
                stat_objects = []  # to be bulk created

                def add_stats(category: str, items, value_key=None, track_obj=None, custom_value=None):
                    for item in items:
                        s = item["statistics"]
                        # Use custom_value (for track name) OR value_key OR fallback
                        value = custom_value or (item.get(value_key) if value_key else "Overall")

                        stat_objects.append(HorseStatistic(
                            horse=horse_obj,
                            category=category,
                            value=value or "Overall",  # fallback for period stats
                            track=track_obj,
                            runs=s["runs"],
                            wins=s["wins"],
                            seconds=s["seconds"],
                            thirds=s["thirds"],
                            win_percentage=Decimal(str(s["winPercentage"])),
                            place_percentage=Decimal(str(s["placePercentage"])),
                            roi=Decimal(str(s["roi"])),
                        ))

                #  ——— Barrier ———
                add_stats("barrier", data.get("horseBarrierStatistics", []), "barrier")

                #  ——— Distance ———
                add_stats("distance", data.get("horseDistanceStatistics", []), "distanceRange")

                # ——— Direction ———
                add_stats("direction", data.get("horseDirectionStatistics", []), "raceDirection")

                # ——— Field Size ———
                add_stats("field_size", data.get("horseFieldSizeStatistics", []), "fieldSize")

                # ——— Group Race ———
                add_stats("group_race", data.get("horseGroupRaceStatistics", []), "groupClass")

                # ——— Resuming ———
                add_stats("resuming", data.get("horseResumingStatistics", []), "resumingRun")

                # ——— Track Condition ———
                add_stats("track_condition", data.get("horseTrackConditionStatistics", []), "trackCondition")

                # ——— Track Surface ———
                add_stats("track_surface", data.get("horseTrackSurfaceStatistics", []), "trackSurface")

                # ——— Weight ———
                add_stats("weight", data.get("horseWeightStatistics", []), "weight")

                # ——— Track-Specific Stats ———
                for item in data.get("horseTrackStatistics", []):
                    track_data = item["track"]
                    track_obj, _ = Track.objects.get_or_create(
                        trackId=track_data["trackId"],
                        defaults={"name": track_data["name"], "countryIso2": track_data.get("countryIso2", "AU")}
                    )
                    add_stats(
                    category="track",
                    items=[item],
                    track_obj=track_obj,
                    custom_value=track_data["name"]  # This is correct
                )

                # ——— Period Stats (12Months, lastTen, asFavourite, etc.) ———
                period_mapping = {
                    "12Months": "Last 12 Months",
                    "lastTen": "Last 10 Starts",
                    "season": "This Season",
                    "asFavourite": "As Favourite",
                    "night": "Night Racing",
                    "career": "Career",
                }
                for key, label in period_mapping.items():
                    if key in stats and stats[key]:
                        s = stats[key]
                        stat_objects.append(HorseStatistic(
                            horse=horse_obj,
                            category="period",
                            value=label,
                            track=None,
                            runs=s["runs"],
                            wins=s["wins"],
                            seconds=s["seconds"],
                            thirds=s["thirds"],
                            win_percentage=Decimal(str(s["winPercentage"])),
                            place_percentage=Decimal(str(s["placePercentage"])),
                            roi=Decimal(str(s["roi"])),
                        ))

                # ——— Bulk upsert with ignore_conflicts ———
                HorseStatistic.objects.bulk_create(
                    stat_objects,
                    update_conflicts=True,
                    update_fields=[
                        "runs", "wins", "seconds", "thirds",
                        "win_percentage", "place_percentage", "roi"
                    ],
                    unique_fields=["horse", "category", "value", "track"]
                )

            print(f"Successfully synced statistics for: {horse_data['name']} (ID: {horse_id})")