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

class Command(BaseCommand):
    help = 'Run the script checker'

    def handle(self, *args, **options):
        # # 1. Fetch ALL trainers for today's race        
        target_date = date.today()
        if options.get('date'):
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()

        start_dt = dj_timezone.make_aware(datetime.combine(target_date, time.min), timezone=timezone.utc)
        end_dt   = dj_timezone.make_aware(datetime.combine(target_date, time.max), timezone=timezone.utc)

        print(start_dt, end_dt)

        trainer_ids = Selection.objects.filter(
            race__meeting__startTimeUtc__range=(start_dt, end_dt)
        ).values_list('trainer_id', flat=True).distinct()
        
        total = trainer_ids.count()

        self.stdout.write(self.style.SUCCESS(f"Found {total} trainers to sync for {target_date}"))

        for i, trainer_id in enumerate(trainer_ids, 1):
            if trainer_id: # Check strictly for not none
                self.stdout.write(f"Syncing {i}/{total} (ID: {trainer_id})...")
                self.sync_trainer_details(trainer_id)

        # for checking
        # trainer = Trainer.objects.first()
        # self.sync_trainer_details(trainer.trainer_id)
    
    
    def sync_trainer_details(self, trainerId: int):
        url = f'{BASE_URL}/horse-racing/v1/statistics/trainer/{trainerId}'
        headers = {"Authorization": f"Bearer {settings.FORMPRO_API_KEY}",
                "Accept": "application/json"}
        try:
            req = requests.get(url, headers=headers, timeout=30)
            req.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch trainer details for {trainerId}: {e}")
            return False
        data = req.json()
        if data:
            trainer_data = data['trainer']
            trainer_Statistics = data['trainerStatistics']
            with transaction.atomic():
                # Create/update the trainer
                trainer_obj, _ = Trainer.objects.update_or_create(
                    trainer_id=trainer_data['trainerId'],
                    defaults={
                        'name': trainer_data['name'],
                        'last_win': trainer_Statistics.get('lastWin'),
                        'total_prize_money': trainer_Statistics.get('totalPrizeMoney'),
                        'average_prize_money': trainer_Statistics.get('averagePrizeMoney'),
                    }
                )
                # Delete old statistics to prevent duplicates and ensure fresh data
                TrainerStatistic.objects.filter(trainer=trainer_obj).delete()
                # Prepare new stats
                trainer_stats = []
                # Updated function with fixes
                def add_trainer_stats(category, items, value_key=None, track=None, jockey=None, custom_value=None):
                    for item in items:
                        s = item['statistics']
                        # Determine value safely
                        if custom_value is not None:
                            final_value = custom_value
                        elif value_key:
                            final_value = item.get(value_key)
                        else:
                            final_value = "Overall"
                        # Safety: Prevent None or empty
                        final_value = str(final_value or "Unknown").strip()
                        if not final_value:
                            final_value = "Unknown"  # Or 'continue' to skip
                        trainer_stats.append(TrainerStatistic(
                            trainer=trainer_obj,
                            category=category,
                            value=final_value,
                            track=track,
                            jockey=jockey,
                            runs=s['runs'],
                            wins=s['wins'],
                            seconds=s['seconds'],
                            thirds=s['thirds'],
                            win_percentage=Decimal(str(s['winPercentage'])),
                            place_percentage=Decimal(str(s['placePercentage'])),
                            roi=Decimal(str(s['roi'])),
                        ))
                # Corrected calls with API-matched keys
                add_trainer_stats("distance", data.get("trainer12MonthsDistanceStatistics", []), value_key="distanceRange")
                add_trainer_stats("group_race", data.get("trainer12MonthsGroupRaceStatistics", []), value_key="groupClass")
                add_trainer_stats("resuming", data.get("trainer12MonthsResumingStatistics", []), value_key="resumingRun")
                # Track stats
                for item in data.get("trainer12MonthsTrackStatistics", []):
                    track_data = item["track"]
                    track_obj, _ = Track.objects.get_or_create(
                        trackId=track_data["trackId"],
                        defaults={"name": track_data["name"], "countryIso2": track_data.get("countryIso2", "AU")}
                    )
                    add_trainer_stats(
                        category="track",
                        items=[item],
                        track=track_obj,
                        custom_value=track_data["name"]
                    )
                # Jockey stats
                for item in data.get("trainer12MonthsJockeyStatistics", []):
                    jockey_data = item["jockey"]
                    jockey_obj, _ = Jockey.objects.get_or_create(
                        jockey_id=jockey_data["jockeyId"],
                        defaults={"name": jockey_data["name"]}
                    )
                    add_trainer_stats(
                        category="jockey",
                        items=[item],
                        jockey=jockey_obj,
                        custom_value=jockey_data["name"]
                    )
                # Period stats
                period_mapping = {
                    "12Months": "Last 12 Months",
                    "lastTen": "Last 10 Starts",
                    "season": "This Season",
                    "asFavourite": "As Favourite",
                    "night": "Night Racing",
                    "career": "Career",
                }
                for key, label in period_mapping.items():
                    if key in trainer_Statistics and trainer_Statistics[key]:
                        s = trainer_Statistics[key]
                        trainer_stats.append(TrainerStatistic(
                            trainer=trainer_obj,
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
                # Bulk create the new stats
                TrainerStatistic.objects.bulk_create(trainer_stats)
            print(f"Successfully synced statistics for: {trainer_data['name']} (ID: {trainerId})")
    
