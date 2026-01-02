from django.core.management.base import BaseCommand
import requests
from datetime import datetime, timezone, time, date
from django.db import transaction
from django.conf import settings
from decimal import Decimal
from dateutil import parser
from dateutil import parser as date_parser
from django.utils import timezone as dj_timezone 
import pytz
from dateutil import parser
from collections import defaultdict

# Model importing:
from horse_race.models.horse import *
from horse_race.models.jockey import *
from horse_race.models.trainer import *
from horse_race.models.track import *
from horse_race.models.meeting import *
from horse_race.models.race import *
from horse_race.models.selection import *
from horse_race.models.predictor import *
from horse_race.models.jockey_horse_static import *

BASE_URL = "https://api.formpro.com.au"

class Command(BaseCommand):
    help = 'Sync field data for meetings'

    def handle(self, *args, **options):

        # target_date = date.today()
        # if options.get('date'):
        #     target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()

        # start_dt = dj_timezone.make_aware(datetime.combine(target_date, time.min), timezone=timezone.utc)
        # end_dt   = dj_timezone.make_aware(datetime.combine(target_date, time.max), timezone=timezone.utc)

        # print(start_dt, end_dt)

        # races = Race.objects.filter(startTimeUtc__range=(start_dt, end_dt))
        # total_races = races.count()

        # if total_races  == 0:
        #     self.stdout.write(self.style.WARNING(f"No races found for date: {target_date}"))
        #     return

        # self.stdout.write(self.style.SUCCESS(f"Found {total_races } races to sync for {target_date}"))

        # for i, race in enumerate(races, 1):
        #     if race.raceId:
        #         self.stdout.write(f"Syncing {i}/{total_races } (Race ID: {race.raceId})...")
        #         self.sync_jockey_horse_stats(race.raceId)

        raceId = Race.objects.first().raceId
        self.sync_jockey_horse_stats(raceId)

    def sync_jockey_horse_stats(self, raceId):
        url = f"{BASE_URL}/horse-racing/v1/form/race/{raceId}"
        headers = {
            "Authorization": f"Bearer {settings.FORMPRO_API_KEY}",
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"API request failed: {e}"))
            return

        data = response.json()
        form_data = data.get("form", [])
        if not form_data:
            self.stdout.write(self.style.WARNING("No form data returned"))
            return

        updated = 0
        for entry in form_data:
            for history in entry.get("history", []):
                sel = history.get("selectionResult", {})
                if sel:
                    jockey = sel.get("jockey", {})
                    jockey_id = jockey.get("jockeyId")
                    horse = sel.get("horse", {})
                    horse_id = horse.get("horseId")
                    
                    if jockey_id and horse_id:
                        stat = entry.get("horse")
                        if stat.get("horseId") == horse_id:
                            stats = entry.get("statistics", {}).get("jockeyHorse", {})
                            try:
                                horse = Horse.objects.get(horse_id=horse_id)        
                                jockey = Jockey.objects.get(jockey_id=jockey_id)    
                            except Horse.DoesNotExist:
                                self.stdout.write(self.style.ERROR(f"Horse not found: {horse_id}"))
                                continue
                            except Jockey.DoesNotExist:
                                self.stdout.write(self.style.ERROR(f"Jockey not found: {jockey_id}"))
                                continue

                            checking = JockeyHorseStatistic.objects.filter(horse=horse, jockey=jockey, updated_at__date=date.today()).first()
                            if checking:
                                continue

                            obj, created = JockeyHorseStatistic.objects.update_or_create(
                                horse=horse,
                                jockey=jockey,
                                defaults={
                                    'runs': stats.get('runs', 0),
                                    'wins': stats.get('wins', 0),
                                    'seconds': stats.get('seconds', 0),
                                    'thirds': stats.get('thirds', 0),
                                    'win_percentage': stats.get('winPercentage', 0),
                                    'place_percentage': stats.get('placePercentage', 0),
                                    'roi': stats.get('roi', 0),
                                    'last_ten_starts': entry.get("statistics", {}).get("lastTenStarts", ""),
                                }
                            )
                            action = "Created" if created else "Updated"
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"{action} → {horse.name} with {jockey.name} | "
                                    f"{stats.get('wins', 0)} wins from {stats.get('runs', 0)} runs "
                                    f"(Win%: {stats.get('winPercentage', 0)}%)"
                                )
                            )
                            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Finished — updated {updated} jockey-horse records for race {raceId}"))







        

        


        


        

        

        





