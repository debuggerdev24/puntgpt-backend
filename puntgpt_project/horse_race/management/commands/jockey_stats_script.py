from django.core.management.base import BaseCommand
import requests
from datetime import datetime, timezone, time, date
from django.db import transaction
from django.conf import settings
from decimal import Decimal
from dateutil import parser

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
    def handle(self, *args, **options):
        '''
        # no need of refreshing all jockeys perday so we will fetch the data of the jockey that participated in today race.
        # target_date = date.today()

        # if options.get('date'):
        #     target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()

        # jockey_ids = Selection.objects.filter(race__metting__date=target_date).values_list('jockey_id',flat=True).distinct()
        # total = jockey_ids.count()

        # print(f"Total jockeys to sync: {total}")

        # for jockey_id in jockey_ids:
        #     self.sync_jockey_detail(jockey_id)
        '''

        # for checking purpose:
        jockey = Jockey.objects.first()
        self.sync_jockey_detail(jockey.jockey_id)


    def sync_jockey_detail(self, jockeyId):
        url = f"{BASE_URL}/horse-racing/v1/statistics/jockey/{jockeyId}"
        headers = {"Authorization": f"Bearer {settings.FORMPRO_API_KEY }"}

        try:
            req = requests.get(url, headers=headers)
            req.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch data for jockey {jockeyId}: {e}")
            return
        
        data = req.json()
        if data:
            jockey = data["jockey"]
            stats = data["jockeyStatistics"]

            # fetching the basic data
            jockey_obj, created = Jockey.objects.update_or_create(
                jockey_id=jockey["jockeyId"],
                defaults={
                "last_win" : stats.get("lastWin"),
                "total_prize_money": stats.get("totalPrizeMoney"),
                "average_prize_money":stats.get("averagePrizeMoney"),
                }
            )
            
            # updating the statistics
            stats_jockey = []

            # deleting the previous data
            JockeyStatistic.objects.filter(jockey=jockey_obj).delete()

            # Function for the bulk creation of jocky data
            def add_jockety_stats(category: str, items, value_key=None, track=None, trainer=None, custom_value=None):
                for item in items:
                    s = item["statistics"] 
                    value = custom_value or (item.get(value_key) if value_key else "Overall")

                    stats_jockey.append(JockeyStatistic(
                        jockey=jockey_obj,
                        category=category,
                        value=value,
                        track=track,
                        trainer=trainer,
                        runs=s["runs"],
                        wins=s["wins"],
                        seconds=s["seconds"],
                        thirds=s["thirds"],
                        win_percentage=Decimal(str(s["winPercentage"])),
                        place_percentage=Decimal(str(s["placePercentage"])),
                        roi=Decimal(str(s["roi"])),
                    ))

            # ____jockey12MonthsBarrierStatistics_________
            add_jockety_stats("barrier", data.get("jockey12MonthsBarrierStatistics", []), "barrier")

            #  ____jockey12MonthsDistanceStatistics_________
            add_jockety_stats("distance", data.get("jockey12MonthsDistanceStatistics", []), "distanceRange")

            #  ____jockey12MonthsFieldSizeStatistics_________
            add_jockety_stats("field_size", data.get("jockey12MonthsFieldSizeStatistics", []), "fieldSize")

            #  ____jockey12MonthsGroupRaceStatistics_________
            add_jockety_stats("group_race", data.get("jockey12MonthsGroupRaceStatistics", []), "groupClass")

            #  ____jockey12MonthsTrackConditionStatistics_________
            add_jockety_stats("track_condition", data.get("jockey12MonthsTrackConditionStatistics", []), "trackCondition")

            #  ____jockey12MonthsTrackStatistics_________
            for item in data.get("jockey12MonthsTrackStatistics", []):
                    track_data = item["track"]
                    track_obj, _ = Track.objects.get_or_create(
                        trackId=track_data["trackId"],
                        defaults={"name": track_data["name"], "countryIso2": track_data.get("countryIso2", "AU")}
                    )
                    add_jockety_stats(
                    category="track",
                    items=[item],
                    track=track_obj,
                    custom_value=track_data["name"]  # This is correct
                )

            #  ____jockey12MonthsTrainerStatistics_________
            # add_jockety_stats("trainer", data.get("jockey12MonthsTrainerStatistics", []), "trainer", value_key="trainerName")
            for item in data.get("jockey12MonthsTrainerStatistics", []):
                    trainer_data = item["trainer"]
                    trainer_obj, _ = Trainer.objects.get_or_create(
                        trainer_id=trainer_data["trainerId"],
                        defaults={"name": trainer_data["name"]}
                    )
                    add_jockety_stats(
                    category="trainer",
                    items=[item],
                    trainer=trainer_obj,
                    custom_value=trainer_data["name"]  # This is correct
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
                    stats_jockey.append(JockeyStatistic(
                        jockey=jockey_obj,
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
            JockeyStatistic.objects.bulk_create(
                stats_jockey,
                update_conflicts=True,
                update_fields=[
                    "runs", "wins", "seconds", "thirds",
                    "win_percentage", "place_percentage", "roi"
                ],
                unique_fields=["jockey", "category", "value", "track", "trainer"],
            )

            print(f"Successfully synced statistics for: {jockey['name']} (ID: {jockeyId})")