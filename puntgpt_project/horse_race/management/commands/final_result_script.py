from django.core.management.base import BaseCommand
from django.core.management.base import BaseCommand
import requests
from datetime import datetime, timezone, time, date
from django.db import transaction
from django.conf import settings
from decimal import Decimal
from dateutil import parser
from dateutil import parser as date_parser
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
    help = 'Sync final result data for meetings'

    def handle(self, *args, **options):
        # 1. Fetch ALL meetings for today's race      
        target_date = date.today()
        if options.get('date'):
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()

        start_dt = dj_timezone.make_aware(datetime.combine(target_date, time.min), timezone=timezone.utc)
        end_dt   = dj_timezone.make_aware(datetime.combine(target_date, time.max), timezone=timezone.utc)

        print(start_dt, end_dt)

        meetings = Meeting.objects.filter(startTimeUtc__range=(start_dt, end_dt))
        total_meetings = meetings.count()

        if total_meetings == 0:
            self.stdout.write(self.style.WARNING(f"No meetings found for date: {target_date}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Found {total_meetings} meetings to sync for {target_date}"))

        for i, meeting in enumerate(meetings, 1):
            if meeting.meetingId:
                self.stdout.write(f"Syncing {i}/{total_meetings} (Meeting ID: {meeting.meetingId})...")
                self.sync_meeting_results(meeting.meetingId)

        # meetingId = Meeting.objects.first().meetingId
        # self.sync_meeting_results(meetingId)

    def sync_meeting_results(self,meetingId: int):
        url = f"https://api.formpro.com.au/horse-racing/v1/results/final/meeting/{meetingId}"
        headers = {"Authorization": f"Bearer {settings.FORMPRO_API_KEY}"}

        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
        except Exception as e:
            print(f"[ERROR] Meeting {meetingId}: {e}")
            return False

        data = resp.json()
        meeting_data = data["meeting"]

        # 1. Ensure Meeting + Track
        track, _ = Track.objects.update_or_create(
            trackId=meeting_data["track"]["trackId"],
            defaults={"name": meeting_data["track"]["name"], "countryIso2": "AU"}
        )
        meeting, _ = Meeting.objects.update_or_create(
            meetingId=meetingId,
            defaults={
                "date": meeting_data["date"],
                "track": track,
                "stage": "Results",
                "isTrial": meeting_data.get("isTrial", False),
            }
        )

        # Containers for bulk operations
        races_to_update = []
        selections_to_create = []
        selections_to_update = []
        history_to_create = []
        history_to_update = []

        # Caches
        horse_cache = {}
        jockey_cache = {}
        trainer_cache = {}  # ← Fixed: was using jockey_cache!

        print(f"[INFO] Syncing {len(data.get('races', []))} races for meeting {meetingId}")

        for race_entry in data.get("races", []):
            race_result = race_entry.get("raceResult")
            selections_data = race_entry.get("selectionResults", [])

            if not race_result:
                print(f"[WARN] Missing raceResult for meeting {meetingId}, skipping race entry")
                continue

            race_id = race_result.get("raceId")

        
            race, created = Race.objects.get_or_create(
            raceId=race_id,
            defaults={
                "meeting": meeting,
                "number": race_result.get("number"),
                "name": race_result.get("name", ""),
                "race_starters": race_result.get("raceStarters"),
            }
        )

            # If race already exists, update fields
            if not created:
                race.meeting = meeting
                race.number = race_result.get("number")
                race.name = race_result.get("name", "")
                race.race_starters = race_result.get("raceStarters")
                races_to_update.append(race)


            winner_sel = second_sel = third_sel = None

            # Pre-fetch existing selections and history
            existing_sels = Selection.objects.filter(race=race).in_bulk(field_name="selectionId")
            # existing_histories = {
            #     (h.horse_id, h.race_id): h
            #     for h in HorseRaceHistory.objects.filter(race=race).select_related('horse')
            # }

            # --------------------------------
            # CASE 2: RACE-ONLY RESULTS (KEY)
            # --------------------------------
            placings = [
                (1, "winnerHorse", "winnerJockey"),
                (2, "secondHorse", "secondJockey"),
                (3, "thirdHorse", "thirdJockey"),
            ]

            for pos, horse_key, jockey_key in placings:
                horse_data = race_result.get(horse_key)
                if not horse_data:
                    continue

                horse, _ = Horse.objects.get_or_create(
                    horse_id=horse_data["horseId"],
                    defaults={"name": horse_data["name"]}
                )

                jockey = None
                jockey_data = race_result.get(jockey_key)
                if jockey_data:
                    jockey, _ = Jockey.objects.get_or_create(
                        jockey_id=jockey_data["jockeyId"],
                        defaults={"name": jockey_data.get("name", "Unknown")}
                    )

                sel_obj, created = Selection.objects.update_or_create(
                    race=race,
                    horse=horse,
                    jockey=jockey,
                    defaults={
                        "result_position": pos,
                    }
                )    
                if pos == 1:
                    winner_sel = sel_obj
                elif pos == 2:
                    second_sel = sel_obj
                elif pos == 3:
                    third_sel = sel_obj 
                
            
            # --------------------------------
            # CASE 1: SELECTIONS + HISTORY
            # --------------------------------
            for sel_data in selections_data:
                if sel_data.get("isScratched"):
                    continue

                # Horse
                horse_id = sel_data["horse"]["horseId"]
                if horse_id not in horse_cache:
                    horse, _ = Horse.objects.get_or_create(
                        horse_id=horse_id,
                        defaults={"name": sel_data["horse"]["name"]}
                    )
                    horse_cache[horse_id] = horse
                horse = horse_cache[horse_id]

                # Jockey
                jockey = None
                if sel_data.get("jockey"):
                    jid = sel_data["jockey"]["jockeyId"]
                    if jid not in jockey_cache:
                        jockey, _ = Jockey.objects.get_or_create(
                            jockey_id=jid,
                            defaults={"name": sel_data["jockey"].get("name", "Unknown")}
                        )
                        jockey_cache[jid] = jockey
                    jockey = jockey_cache[jid]

                
                trainer = None
                if sel_data.get("trainer"):
                    tid = sel_data["trainer"]["trainerId"]
                    if tid not in trainer_cache:
                        trainer, _ = Trainer.objects.get_or_create(
                            trainer_id=tid,
                            defaults={"name": sel_data["trainer"].get("name", "Unknown")}
                        )
                        trainer_cache[tid] = trainer
                    trainer = trainer_cache[tid]

                sel_id = sel_data["selectionId"]
                pos = sel_data.get("result")

                # Selection fields
                selection_fields = {
                    "race": race,
                    "horse": horse,
                    "jockey": jockey,
                    "trainer": trainer,
                    "number": sel_data.get("number"),
                    "barrier": sel_data.get("barrier"),
                    "weight_carried": sel_data.get("weightCarried"),
                    "starting_price": sel_data.get("startingPrice"),
                    "result_position": pos,
                    "margin_decimal": sel_data.get("marginDecimal"),
                    "in_running_positions": sel_data.get("inRunning", []),
                    "isScratched": False,
                }

                if sel_id in existing_sels:
                    sel_obj = existing_sels[sel_id]
                    for k, v in selection_fields.items():
                        setattr(sel_obj, k, v)
                    selections_to_update.append(sel_obj)
                else:
                    sel_obj = Selection(selectionId=sel_id, **selection_fields)
                    selections_to_create.append(sel_obj)

                # Capture placings
                if pos == 1:
                    winner_sel = sel_obj
                elif pos == 2:
                    second_sel = sel_obj
                elif pos == 3:
                    third_sel = sel_obj

                # HorseRaceHistory
                # history_key = (horse.horse_id, race.raceId)
                # if history_key not in existing_histories:
                #     history_to_create.append(
                #         HorseRaceHistory(
                #             horse=horse, race=race, selection=sel_obj,
                #             finish_position=pos,
                #             margin=sel_data.get("marginDecimal"),
                #             starting_price=sel_data.get("startingPrice"),
                #             in_running=sel_data.get("inRunning", []),
                #             is_trial=meeting.isTrial
                #         )
                #     )
                # else:
                #     hist = existing_histories[history_key]
                #     hist.selection = sel_obj
                #     hist.finish_position = pos
                #     hist.margin = sel_data.get("marginDecimal")
                #     hist.starting_price = sel_data.get("startingPrice")
                #     hist.in_running = sel_data.get("inRunning", [])
                #     history_to_update.append(hist)

            # Set placings on race
            if winner_sel:
                race.winner = winner_sel
            if second_sel:
                race.second = second_sel
            if third_sel:
                race.third = third_sel
            race.save(update_fields=["winner", "second", "third"])

        # BULK OPERATIONS
        if races_to_update:
            Race.objects.bulk_update(
                races_to_update,
                fields=[
                    "meeting", "number", "name", 
                    "race_starters", "isAbandoned", "stage",
                    "winner", "second", "third",
                    # "official_time", "last_600_time",
                    # "winner_horse", "winner_jockey",
                ]
            )

        if selections_to_create:
            Selection.objects.bulk_create(selections_to_create, ignore_conflicts=True)
        if selections_to_update:
            Selection.objects.bulk_update(
                selections_to_update,
                fields=[
                    "horse", "jockey", "trainer", "number", "barrier", "weight_carried",
                    "starting_price", "result_position", "margin_decimal",
                    "in_running_positions", "isScratched"
                ]
            )

        # if history_to_create:
        #     HorseRaceHistory.objects.bulk_create(history_to_create, ignore_conflicts=True)
        # if history_to_update:
        #     HorseRaceHistory.objects.bulk_update(
        #         history_to_update,
        #         fields=["selection", "finish_position", "margin", "starting_price", "in_running"]
        #     )

        print(f"[SUCCESS] Meeting {meetingId} synced with bulk operations")
        return True