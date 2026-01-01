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

# def time_conversion(time):
#     australia = pytz.timezone("Australia/Sydney")
#     current_time_str = time 

#     # Remove the "Z" and convert the string to a datetime object (in UTC)
#     current_time = datetime.strptime(current_time_str[:-1], "%Y-%m-%dT%H:%M:%S%z")

#     # Convert the datetime object to the Australia/Sydney timezone
#     current_time_in_sydney = current_time.astimezone(australia)

#     return current_time_in_sydney

def time_conversion(time_str):
    australia = pytz.timezone("Australia/Sydney")
    utc = pytz.UTC

    # Fix invalid "+00:00Z"
    if time_str.endswith("+00:00Z"):
        time_str = time_str.replace("+00:00Z", "Z")

    dt_utc = parser.isoparse(time_str).astimezone(utc)
    dt_aus = dt_utc.astimezone(australia)

    return dt_aus

class Command(BaseCommand):
    help = 'Sync field data for meetings'

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
                self.sync_field_for_meeting(meeting.meetingId)

        # meetingId = Meeting.objects.first().meetingId
        # self.sync_field_for_meeting(meetingId)

    def sync_field_for_meeting(self, meetingId):
        url = f"https://api.formpro.com.au/horse-racing/v1/field/meeting/{meetingId}"
        headers = {
            "Authorization": f"Bearer {settings.FORMPRO_API_KEY}",
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching field data for meeting {meetingId}: {e}"))
            return False

        data = response.json()
        meeting_data = data.get("meeting")
        if not meeting_data:
            self.stdout.write(self.style.WARNING("No meeting data returned"))
            return False

        track_data = meeting_data.get("track")
        races_data = data.get("races", [])

        # 1. Update Meeting + Track (with extra field data)
        meeting_obj, _ = Meeting.objects.update_or_create(
            meetingId=meeting_data["meetingId"],
            defaults={
                "name": meeting_data.get("name"),
                "category": meeting_data.get("category"),
                "meeting_type": meeting_data.get("type"),  # Note: API uses "type", not "meetingType"
                "rail_position": meeting_data.get("railPosition"),
                "time_slot": meeting_data.get("timeSlot"),
                "weather_condition": meeting_data.get("weatherCondition"),
                "temperature": meeting_data.get("temperature"),
                "tab_status": meeting_data.get("tabStatus") or False,
            }
        )

        track_obj, _ = Track.objects.update_or_create(
            trackId=track_data["trackId"],
            defaults={
                "name": track_data["name"],
                "countryIso2": track_data["countryIso2"],
                "address": track_data.get("address") or "",
                "circumference": track_data.get("circumference"),
                "straight": track_data.get("straight"),
                "is_clockwise": track_data.get("isClockwise"),
                "sprint_lane": track_data.get("sprintLane"),
                "surface": track_data.get("surface") or "",
                "track_code": track_data.get("trackCode") or "",
            }
        )

        # Ensure meeting has correct track
        meeting_obj.track = track_obj
        meeting_obj.save()

        # Prepare lists for bulk operations
        races_to_create = []
        selections_to_create = []
        horses_to_update = []
        jockeys_to_update = []
        trainers_to_update = []

        # Cache for objects to avoid duplicates in this sync
        horse_cache = {}
        jockey_cache = {}
        trainer_cache = {}

        for race_wrapper in races_data:
            race_info = race_wrapper.get("race")
            if not race_info:
                continue

            start_time_str = race_info.get("startTimeUtc")
            if start_time_str:
                # Remove trailing 'Z' if offset is already +00:00 (common API bug)
                if start_time_str.endswith("+00:00Z"):
                    start_time_str = start_time_str[:-1]  # Remove the final 'Z'
                start_time_parsed = parser.parse(start_time_str)
            else:
                start_time_parsed = None
            # Handle Race
            race_defaults = {
                "meeting": meeting_obj,
                "number": race_info["number"],
                "name": race_info.get("name", ""),
                "distance": race_info.get("distance"),
                "distance_units": race_info.get("distanceUnit"),
                "prize_money": Decimal(str(race_info["prizeMoney"])) if race_info.get("prizeMoney") else None,
                "start_type": race_info.get("startType"),
                # "startTimeUtc": race_info.get("startTimeUtc"),
                "startTimeUtc": start_time_parsed,
                "startTimeUtc_raw": race_info.get("startTimeUtc"),
                'startTimeUtcAus':time_conversion(race_info.get("startTimeUtc")),
                "track_condition": race_info.get("trackConditionOverall"),
                "track_condition_rating": race_info.get("trackConditionRating"),
                "track_type": race_info.get("trackType"),
                "entry_conditions": race_info.get("entryConditions", {}),
                "isAbandoned": race_info.get("isAbandoned", False),
            }

            race_obj, created = Race.objects.update_or_create(
                raceId=race_info["raceId"],
                defaults=race_defaults
            )

            # Process all selections in this race
            for sel_data in race_wrapper.get("selections", []):
                horse_data = sel_data.get("horse", {})
                jockey_data = sel_data.get("jockey", {})
                trainer_data = sel_data.get("trainer", {})

                horse_id = horse_data.get("horseId")
                jockey_id = jockey_data.get("jockeyId")
                trainer_id = trainer_data.get("trainerId")

                # === Horse ===
                if horse_id and horse_id not in horse_cache:
                    horse_obj, _ = Horse.objects.update_or_create(
                        horse_id=horse_id,
                        defaults={
                            "name": horse_data.get("name", ""),
                            "age": horse_data.get("age"),
                            "colour": horse_data.get("colour"),
                            "sex": horse_data.get("sex"),
                            "foal_date": horse_data.get("foalDate"),
                            "sire": horse_data.get("sire"),
                            "dam": horse_data.get("dam"),
                            "damsire": horse_data.get("damsire"),
                            "breeder": horse_data.get("breeder"),
                            "owners": horse_data.get("owners"),
                            "training_location": horse_data.get("trainingLocation"),
                        }
                    )
                    horse_cache[horse_id] = horse_obj

                # === Jockey ===
                if jockey_id and jockey_id not in jockey_cache:
                    jockey_obj, _ = Jockey.objects.update_or_create(
                        jockey_id=jockey_id,
                        defaults={
                            "name": jockey_data.get("name", ""),
                            "country": jockey_data.get("country"),
                            "state": jockey_data.get("state"),
                            "is_apprentice": jockey_data.get("isApprentice", False),
                        }
                    )
                    jockey_cache[jockey_id] = jockey_obj

                # === Trainer ===
                if trainer_id and trainer_id not in trainer_cache:
                    trainer_obj, _ = Trainer.objects.update_or_create(
                        trainer_id=trainer_id,
                        defaults={
                            "name": trainer_data.get("name", ""),
                            "location": trainer_data.get("location"),
                            "postcode": trainer_data.get("postcode"),
                            "state": trainer_data.get("state"),
                            "title": trainer_data.get("title"),
                        }
                    )
                    trainer_cache[trainer_id] = trainer_obj

                # === Selection ===
                selection_defaults = {
                    "race": race_obj,
                    "horse": horse_cache.get(horse_id),
                    "jockey": jockey_cache.get(jockey_id),
                    "trainer": trainer_cache.get(trainer_id),
                    "number": sel_data.get("number"),
                    "barrier": sel_data.get("barrier"),
                    "weight": Decimal(str(sel_data["weight"])) if sel_data.get("weight") else None,
                    "claim": sel_data.get("claim"),
                    "handicap_rating": sel_data.get("handicapRating"),
                    "gear": sel_data.get("gear"),
                    "gear_changes": sel_data.get("gearChanges"),
                    "racing_colours": sel_data.get("racingColours"),
                    "silks_image": sel_data.get("silksImage"),
                    "isScratched": sel_data.get("isScratched", False),
                    "isEmergency": sel_data.get("isEmergency", False),
                }

                Selection.objects.update_or_create(
                    selectionId=sel_data["selectionId"],
                    defaults=selection_defaults
                )

        self.stdout.write(self.style.SUCCESS(f"Successfully synced field data for meeting {meetingId}"))
        return True


