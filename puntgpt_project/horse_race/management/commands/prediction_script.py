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
                self.sync_prediction(meeting.meetingId)

        # meetingId = Meeting.objects.first().meetingId   
        # self.sync_prediction(meetingId)


    # 5.prediction (/horse-racing/v1/predictor/meeting/{meetingId})
    def sync_prediction(self, meetingId):
        url = f"{BASE_URL}/horse-racing/v1/predictor/meeting/{meetingId}"
        headers = {"Authorization": f"Bearer {settings.FORMPRO_API_KEY}",
                "Accept": "application/json"}
        
        try:
            req= requests.get(url, headers=headers)
            req.raise_for_status()
        except Exception as e:
            print(f"Error fetching prediction data: {e}")
            return

        data = req.json()
        ratings_to_save = []
        if data:
            with transaction.atomic():
                for race_wrapper in data["races"]: 
                    for sel_wrapper in race_wrapper.get("selections", []):
                        sel_data = sel_wrapper["selection"]
                        selection_id = sel_data["selectionId"]

                        try:
                            selection_obj = Selection.objects.get(selectionId=selection_id)
                        except Exception as e:
                            print(f"Error fetching selection data: {e}")
                            continue
    
                        # Loop through ALL predictor ratings (BALANCED, WET_TRACK, etc.)
                        for rating in sel_wrapper.get("predictorRatings", []):
                            preset_id = rating["presetId"]
                            preset_name = rating["presetName"]
                            norm_rating = Decimal(str(rating["normalisedRating"]))

                            # Get or create the Preset
                            preset_obj, _ = PredictorPreset.objects.get_or_create(
                                preset_id=preset_id,
                                defaults={"name": preset_name}
                            )

                            ratings_to_save.append(PredictorRating(
                                selection=selection_obj,
                                preset=preset_obj,
                                normalised_rating=norm_rating,
                                # rating_100=int(round(norm_rating * 100))  # ← your genius field
                            ))

                PredictorRating.objects.bulk_create(
                ratings_to_save,
                update_conflicts=True,
                update_fields=["normalised_rating",],
                unique_fields=["selection", "preset"]
            )

        print(f"Success: Synced {len(ratings_to_save)} predictor ratings for meeting {meetingId}")
        return True

