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


# identifier script
# script run: python manage.py script_checker --date=2025-12-13
class Command(BaseCommand):
    help = 'Run the script checker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to sync (YYYY-MM-DD)',
        )

    def handle(self, *args, **options):
        # Parse --date input or use today
        date_input = options.get('date')
        if date_input:
            try:
                local_date = datetime.strptime(date_input, "%Y-%m-%d").date()
            except ValueError:
                print(f"❌ Invalid date format: {date_input}")
                return
        else:
            local_date = date.today()

        # Convert local date to UTC midnight
        utc_datetime = datetime.combine(local_date, time.min).replace(tzinfo=timezone.utc)
        date_str = utc_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")  # 'YYYY-MM-DDT00:00:00Z'

        self.stdout.write(self.style.SUCCESS(f'Syncing data for {date_str}...'))

        self.sync_horse_race_data(date_str)

    # 1.identifier script
    @transaction.atomic
    def sync_horse_race_data(self, date_str: str):

        # primary importing of meeting by date 
        url = f"{BASE_URL}/horse-racing/v1/identifiers/meeting/{date_str}"
        headers ={ "Authorization": f"Bearer {settings.FORMPRO_API_KEY}",
                    "Accept": "application/json"}
        
        try:
            req= requests.get(url, headers=headers, timeout=90)
            req.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch data for date {date_str}: {e}")
            return
        
        data = req.json()
        print(data)
        for meeting_wrapper in data:
            print("Entering the meeting wrapper block")
            # for entering the meeting and track section
            meeting_data = meeting_wrapper["meeting"]
            track_data = meeting_data["track"]
            races_data = meeting_wrapper.get("races", [])  # ← FIXED!

            with transaction.atomic():

                # 1. track table details
                track_obj, _ = Track.objects.update_or_create(
                    trackId=track_data["trackId"],
                    defaults={
                        "name": track_data["name"],
                        "countryIso2": track_data.get("countryIso2", "AU")
                    }
                )

                start_time_str = meeting_data.get("startTimeUtc")
                if start_time_str and start_time_str.endswith('Z') and ('+' in start_time_str or '-' in start_time_str):
                    start_time_str = start_time_str[:-1]  # Strip invalid trailing Z

                # 2.meeting table details
                meeting_obj, _ = Meeting.objects.update_or_create(
                    meetingId=meeting_data["meetingId"],
                    defaults={
                        "date": parser.parse(meeting_data["date"]).date(),
                        "track": track_obj,
                        "isTrial": meeting_data["isTrial"],
                        "stage": meeting_data["stage"],
                        # "startTimeUtc": parser.isoparse(start_time_str) if start_time_str else None,
                        "startTimeUtc" : start_time_str,
                        "startTimeUtc_raw" : start_time_str
                    }
                )
                race_obj = []   #list use append method()
                selection_obj = []
                horse_ids = []
                trainer_ids = []
                jockey_ids = []
                

                # 3. Loop ALL races
                for race_wrapper in races_data:
                    print("Entering the race wrapper block")
                    race_data = race_wrapper["race"]

                    # race table details
                    race_obj.append(Race(
                    raceId=race_data["raceId"],
                    meeting=meeting_obj,
                    number=race_data["number"],
                    stage=race_data.get("stage", "Unknown"),  # or "Pending", "FinalFields", etc.
                    isAbandoned=race_data.get("isAbandoned", False),
                ))

                    # 4. Loop ALL selections in this race
                    for sel in race_wrapper.get("selections", []):

                        print("Entering the selection wrapper block")

                        horse_id = sel["horse"]["horseId"]
                        jockey_id = sel.get("jockey", {}).get("jockeyId")
                        trainer_id = sel.get("trainer", {}).get("trainerId")

                        # horse table details
                        horse_ids.append((horse_id, sel["horse"]["name"]))
                        if jockey_id:
                            jockey_ids.append((jockey_id, sel["jockey"]["name"]))
                        if trainer_id:
                            trainer_ids.append((trainer_id, sel["trainer"]["name"]))
                        
                        # selection table details
                        selection_obj.append(Selection(
                            selectionId=sel["selectionId"],
                            race_id=race_data["raceId"],   # temp — fixed after bulk_create
                            horse_id=horse_id,
                            jockey_id=jockey_id,
                            trainer_id=trainer_id,
                            number=sel.get("number"),
                            isScratched=sel.get("isScratched", False),
                        ))

                # bulk creation
                Race.objects.bulk_create(race_obj, ignore_conflicts=True)

                # ——— HORSES: Create new + Update names if changed ———
                horse_updates = []
                horse_creates = []

                for horse_id, name in horse_ids:
                    # Try to get existing horse
                    try:
                        horse = Horse.objects.only('name').get(horse_id=horse_id)
                        if horse.name != name:
                            horse.name = name
                            horse_updates.append(horse)
                    except Horse.DoesNotExist:
                        horse_creates.append(Horse(horse_id=horse_id, name=name))

                # Bulk create new ones
                if horse_creates:
                    Horse.objects.bulk_create(horse_creates, ignore_conflicts=True)

                # Bulk update changed names
                if horse_updates:
                    Horse.objects.bulk_update(horse_updates, ['name'])

                # ——— SAME FOR JOCKEYS ———
                jockey_updates = []
                jockey_creates = []

                for jid, name in jockey_ids:
                    try:
                        jockey = Jockey.objects.only('name').get(jockey_id=jid)
                        if jockey.name != name:
                            jockey.name = name
                            jockey_updates.append(jockey)
                    except Jockey.DoesNotExist:
                        jockey_creates.append(Jockey(jockey_id=jid, name=name))

                if jockey_creates:
                    Jockey.objects.bulk_create(jockey_creates, ignore_conflicts=True)
                if jockey_updates:
                    Jockey.objects.bulk_update(jockey_updates, ['name'])

                # ——— SAME FOR TRAINERS ———
                trainer_updates = []
                trainer_creates = []

                for tid, name in trainer_ids:
                    try:
                        trainer = Trainer.objects.only('name').get(trainer_id=tid)
                        if trainer.name != name:
                            trainer.name = name
                            trainer_updates.append(trainer)
                    except Trainer.DoesNotExist:
                        trainer_creates.append(Trainer(trainer_id=tid, name=name))

                if trainer_creates:
                    Trainer.objects.bulk_create(trainer_creates, ignore_conflicts=True)
                if trainer_updates:
                    Trainer.objects.bulk_update(trainer_updates, ['name'])

                # ——— SELECTIONS (safe now) ———
                Selection.objects.bulk_create(selection_obj, ignore_conflicts=True)






