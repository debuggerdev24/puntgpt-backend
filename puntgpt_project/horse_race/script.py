# import requests
# from datetime import date, timedelta
# from django.db import transaction
# from models.horse import Horse
# from models.jockey import Jockey
# from models.trainer import Trainer
# from models.race import Race
# from models.meeting import Meeting
# from models.selection import Selection
# from django.conf import settings
# from decimal import Decimal

# # Model importing:
# from horse_race.models.horse import *
# from horse_race.models.jockey import *
# from horse_race.models.trainer import *
# from horse_race.models.track import *
# from horse_race.models.meeting import *
# from horse_race.models.race import *
# from horse_race.models.selection import *
# from horse_race.models.predictor import *

# BASE_URL = "https://api.formpro.com.au"

# # 1.identifier script
# @transaction.atomic
# def sync_horse_race_data(date_str: str):

#     # primary importing of meeting by date 
#     url = f"{BASE_URL}/horse-racing/v1/identifiers/meeting/{date_str}"
#     headers ={ "Authorization": f"Bearer {settings.FORMPRO_API_KEY}",
#                 "Accept": "application/json"}
#     try:
#         req= requests.get(url, headers=headers, timeout=90)
#         req.raise_for_status()
#     except Exception as e:
#         print(f"Failed to fetch data for date {date_str}: {e}")
#         return
    
#     data = req.json()
#     for meeting_wrapper in data:
#         # for entering the meeting and track section
#         meeting_data = meeting_wrapper["meeting"]
#         track_data = meeting_data["track"]
#         races_data = meeting_wrapper.get("races", [])  # ← FIXED!

#         with transaction.atomic():

#             # 1. track table details
#             track_obj, _ = Track.objects.update_or_create(
#                 trackId=track_data["trackId"],
#                 defaults={
#                     "name": track_data["name"],
#                     "countryIso2": track_data.get("countryIso2", "AU")
#                 }
#             )

#             # 2.meeting table details
#             meeting_obj, _ = Meeting.objects.update_or_create(
#                 meetingId=meeting_data["meetingId"],
#                 defaults={
#                     "date": meeting_data["date"],
#                     "track": track_obj,
#                     "isTrial": meeting_data["isTrial"],
#                     "stage": meeting_data["stage"],
#                     "startTimeUtc": meeting_data.get("startTimeUtc"),
#                 }
#             )
#             race_obj = []   #list use append method()
#             selection_obj = []
#             horse_ids = []
#             trainer_ids = []
#             jockey_ids = []
            

#             # 3. Loop ALL races
#             for race_wrapper in races_data:
#                 race_data = race_wrapper["race"]

#                 # race table details
#                 race_obj.append(Race(
#                     raceId=race_data["raceId"],
#                     meeting=meeting_obj,
#                     number=race_data["number"],
#                     stage=race_data["stage"],
#                     isAbandoned=race_data.get("isAbandoned", False),
#                 ))

#                 # 4. Loop ALL selections in this race
#                 for sel in race_wrapper.get("selections", []):

#                     horse_id = sel["horse"]["horseId"]
#                     jockey_id = sel.get("jockey", {}).get("jockeyId")
#                     trainer_id = sel.get("trainer", {}).get("trainerId")

#                     # horse table details
#                     horse_ids.append((horse_id, sel["horse"]["name"]))
#                     if jockey_id:
#                         jockey_ids.append((jockey_id, sel["jockey"]["name"]))
#                     if trainer_id:
#                         trainer_ids.append((trainer_id, sel["trainer"]["name"]))
                    
#                     # selection table details
#                     selection_obj.append(Selection(
#                         selectionId=sel["selectionId"],
#                         race_id=race_data["raceId"],   # temp — fixed after bulk_create
#                         horse_id=horse_id,
#                         jockey_id=jockey_id,
#                         trainer_id=trainer_id,
#                         number=sel.get("number"),
#                         isScratched=sel.get("isScratched", False),
#                     ))

#             # bulk creation
#             Race.objects.bulk_create(race_obj, ignore_conflicts=True)

#             # ——— HORSES: Create new + Update names if changed ———
#             horse_updates = []
#             horse_creates = []

#             for horse_id, name in horse_ids:
#                 # Try to get existing horse
#                 try:
#                     horse = Horse.objects.only('name').get(horse_id=horse_id)
#                     if horse.name != name:
#                         horse.name = name
#                         horse_updates.append(horse)
#                 except Horse.DoesNotExist:
#                     horse_creates.append(Horse(horse_id=horse_id, name=name))

#             # Bulk create new ones
#             if horse_creates:
#                 Horse.objects.bulk_create(horse_creates, ignore_conflicts=True)

#             # Bulk update changed names
#             if horse_updates:
#                 Horse.objects.bulk_update(horse_updates, ['name'])

#             # ——— SAME FOR JOCKEYS ———
#             jockey_updates = []
#             jockey_creates = []

#             for jid, name in jockey_ids:
#                 try:
#                     jockey = Jockey.objects.only('name').get(jockey_id=jid)
#                     if jockey.name != name:
#                         jockey.name = name
#                         jockey_updates.append(jockey)
#                 except Jockey.DoesNotExist:
#                     jockey_creates.append(Jockey(jockey_id=jid, name=name))

#             if jockey_creates:
#                 Jockey.objects.bulk_create(jockey_creates, ignore_conflicts=True)
#             if jockey_updates:
#                 Jockey.objects.bulk_update(jockey_updates, ['name'])

#             # ——— SAME FOR TRAINERS ———
#             trainer_updates = []
#             trainer_creates = []

#             for tid, name in trainer_ids:
#                 try:
#                     trainer = Trainer.objects.only('name').get(trainer_id=tid)
#                     if trainer.name != name:
#                         trainer.name = name
#                         trainer_updates.append(trainer)
#                 except Trainer.DoesNotExist:
#                     trainer_creates.append(Trainer(trainer_id=tid, name=name))

#             if trainer_creates:
#                 Trainer.objects.bulk_create(trainer_creates, ignore_conflicts=True)
#             if trainer_updates:
#                 Trainer.objects.bulk_update(trainer_updates, ['name'])

#             # ——— SELECTIONS (safe now) ———
#             Selection.objects.bulk_create(selection_obj, ignore_conflicts=True)



# # 2.Advances statistics horse detail api
# def sync_horse_detail(horse_id: int):
#     url = f"{BASE_URL}/horse-racing/v1/statistics/horse/{horse_id}"
#     headers = {"Authorization": f"Bearer {settings.FORMPRO_API_KEY}"}
#     try:
#         req = requests.get(url, headers=headers)
#         req.raise_for_status()
#     except Exception as e:
#         print(f"API error {e} for horse {horse_id}")
#         return False
  
#     data = req.json()

#     if data:
#         # Fetching the horse id
#         horse_data = data["horse"]
#         stats = data["horseStatistics"]

#         with transaction.atomic():
#             # Fetching the horse row
#             horse_obj, created = Horse.objects.update_or_create(
#             horse_id=horse_data["horseId"],
#             defaults={
#                 "name": horse_data["name"],
#                 "last_win": stats.get("lastWin"),
#                 "average_prize_money": stats.get("averagePrizeMoney"),
#                 "total_prize_money": stats.get("totalPrizeMoney"),
#             }
#         )

#             # updating the statistics
#             stat_objects = []  # to be bulk created

#             def add_stats(category: str, items, value_key=None, track_obj=None, custom_value=None):
#                 for item in items:
#                     s = item["statistics"]
#                     # Use custom_value (for track name) OR value_key OR fallback
#                     value = custom_value or (item.get(value_key) if value_key else "Overall")

#                     stat_objects.append(HorseStatistic(
#                         horse=horse_obj,
#                         category=category,
#                         value=value or "Overall",  # fallback for period stats
#                         track=track_obj,
#                         runs=s["runs"],
#                         wins=s["wins"],
#                         seconds=s["seconds"],
#                         thirds=s["thirds"],
#                         win_percentage=Decimal(str(s["winPercentage"])),
#                         place_percentage=Decimal(str(s["placePercentage"])),
#                         roi=Decimal(str(s["roi"])),
#                     ))

#             #  ——— Barrier ———
#             add_stats("barrier", data.get("horseBarrierStatistics", []), "barrier")

#             #  ——— Distance ———
#             add_stats("distance", data.get("horseDistanceStatistics", []), "distanceRange")

#             # ——— Direction ———
#             add_stats("direction", data.get("horseDirectionStatistics", []), "raceDirection")

#             # ——— Field Size ———
#             add_stats("field_size", data.get("horseFieldSizeStatistics", []), "fieldSize")

#             # ——— Group Race ———
#             add_stats("group_race", data.get("horseGroupRaceStatistics", []), "groupClass")

#             # ——— Resuming ———
#             add_stats("resuming", data.get("horseResumingStatistics", []), "resumingRun")

#             # ——— Track Condition ———
#             add_stats("track_condition", data.get("horseTrackConditionStatistics", []), "trackCondition")

#             # ——— Track Surface ———
#             add_stats("track_surface", data.get("horseTrackSurfaceStatistics", []), "trackSurface")

#             # ——— Weight ———
#             add_stats("weight", data.get("horseWeightStatistics", []), "weight")

#             # ——— Track-Specific Stats ———
#             for item in data.get("horseTrackStatistics", []):
#                 track_data = item["track"]
#                 track_obj, _ = Track.objects.get_or_create(
#                     trackId=track_data["trackId"],
#                     defaults={"name": track_data["name"], "countryIso2": track_data.get("countryIso2", "AU")}
#                 )
#                 add_stats(
#                 category="track",
#                 items=[item],
#                 track_obj=track_obj,
#                 custom_value=track_data["name"]  # This is correct
#             )

#             # ——— Period Stats (12Months, lastTen, asFavourite, etc.) ———
#             period_mapping = {
#                 "12Months": "Last 12 Months",
#                 "lastTen": "Last 10 Starts",
#                 "season": "This Season",
#                 "asFavourite": "As Favourite",
#                 "night": "Night Racing",
#                 "career": "Career",
#             }
#             for key, label in period_mapping.items():
#                 if key in stats and stats[key]:
#                     s = stats[key]
#                     stat_objects.append(HorseStatistic(
#                         horse=horse_obj,
#                         category="period",
#                         value=label,
#                         track=None,
#                         runs=s["runs"],
#                         wins=s["wins"],
#                         seconds=s["seconds"],
#                         thirds=s["thirds"],
#                         win_percentage=Decimal(str(s["winPercentage"])),
#                         place_percentage=Decimal(str(s["placePercentage"])),
#                         roi=Decimal(str(s["roi"])),
#                     ))

#             # ——— Bulk upsert with ignore_conflicts ———
#             HorseStatistic.objects.bulk_create(
#                 stat_objects,
#                 update_conflicts=True,
#                 update_fields=[
#                     "runs", "wins", "seconds", "thirds",
#                     "win_percentage", "place_percentage", "roi"
#                 ],
#                 unique_fields=["horse", "category", "value", "track"]
#             )

#         print(f"Successfully synced statistics for: {horse_data['name']} (ID: {horse_id})")



# # 3. Advanced statistics jockey detail api
# def sync_jockey_details(jockeyId):
#     url = f"{BASE_URL}/horse-racing/v1/statistics/jockey/{jockeyId}"
#     headers = {"Authorization": f"Bearer {settings.FORMPRO_API_KEY }"}

#     try:
#         req = requests.get(url, headers=headers)
#         req.raise_for_status()
#     except Exception as e:
#         print(f"Failed to fetch data for jockey {jockeyId}: {e}")
#         return
    
#     data = req.json()
#     if data:
#         jockey = data["jockey"]
#         stats = data["jockeyStatistics"]

#         # fetching the basic data
#         jockey_obj, created = Jockey.objects.update_or_create(
#             jockeyId=jockey["jockeyId"],
#             defaults={
#             "last_win" : stats.get("lastWin"),
#             "total_prize_money": stats.get("totalPrizeMoney"),
#             "average_prize_money":stats.get("averagePrizeMoney"),
#             }
#         )
        
#         # updating the statistics
#         stats_jockey = []

#         # Function for the bulk creation of jocky data
#         def add_jockety_stats(category: str, items, value_key=None, track=None, trainer=None, custom_value=None):
#             for item in items:
#                 s = item["statistics"] 
#                 value = custom_value or (item.get(value_key) if value_key else "Overall")

#                 stats_jockey.append(JockeyStatistic(
#                     jockey=jockey_obj,
#                     category=category,
#                     value=value,
#                     track=track,
#                     trainer=trainer,
#                     runs=s["runs"],
#                     wins=s["wins"],
#                     seconds=s["seconds"],
#                     thirds=s["thirds"],
#                     win_percentage=Decimal(str(s["winPercentage"])),
#                     place_percentage=Decimal(str(s["placePercentage"])),
#                     roi=Decimal(str(s["roi"])),
#                 ))

#         # ____jockey12MonthsBarrierStatistics_________
#         add_jockety_stats("barrier", data.get("jockey12MonthsBarrierStatistics", []), "barrier")

#         #  ____jockey12MonthsDistanceStatistics_________
#         add_jockety_stats("distance", data.get("jockey12MonthsDistanceStatistics", []), "distanceRange")

#         #  ____jockey12MonthsFieldSizeStatistics_________
#         add_jockety_stats("field_size", data.get("jockey12MonthsFieldSizeStatistics", []), "fieldSize")

#         #  ____jockey12MonthsGroupRaceStatistics_________
#         add_jockety_stats("group_race", data.get("jockey12MonthsGroupRaceStatistics", []), "groupClass")

#         #  ____jockey12MonthsTrackConditionStatistics_________
#         add_jockety_stats("track_condition", data.get("jockey12MonthsTrackConditionStatistics", []), "trackCondition")

#         #  ____jockey12MonthsTrackStatistics_________
#         for item in data.get("jockey12MonthsTrackStatistics", []):
#                 track_data = item["track"]
#                 track_obj, _ = Track.objects.get_or_create(
#                     trackId=track_data["trackId"],
#                     defaults={"name": track_data["name"], "countryIso2": track_data.get("countryIso2", "AU")}
#                 )
#                 add_jockety_stats(
#                 category="track",
#                 items=[item],
#                 track=track_obj,
#                 custom_value=track_data["name"]  # This is correct
#             )

#         #  ____jockey12MonthsTrainerStatistics_________
#         # add_jockety_stats("trainer", data.get("jockey12MonthsTrainerStatistics", []), "trainer", value_key="trainerName")
#         for item in data.get("jockey12MonthsTrainerStatistics", []):
#                 trainer_data = item["trainer"]
#                 trainer_obj, _ = Trainer.objects.get_or_create(
#                     trainerId=trainer_data["trainerId"],
#                     defaults={"name": trainer_data["name"]}
#                 )
#                 add_jockety_stats(
#                 category="trainer",
#                 items=[item],
#                 trainer=trainer_obj,
#                 custom_value=trainer_data["name"]  # This is correct
#             )
                

#         # ——— Period Stats (12Months, lastTen, asFavourite, etc.) ———
#         period_mapping = {
#             "12Months": "Last 12 Months",
#             "lastTen": "Last 10 Starts",
#             "season": "This Season",
#             "asFavourite": "As Favourite",
#             "night": "Night Racing",
#             "career": "Career",
#         }
#         for key, label in period_mapping.items():
#             if key in stats and stats[key]:
#                 s = stats[key]
#                 stats_jockey.append(JockeyStatistic(
#                     jockey=jockey_obj,
#                     category="period",
#                     value=label,
#                     track=None,
#                     runs=s["runs"],
#                     wins=s["wins"],
#                     seconds=s["seconds"],
#                     thirds=s["thirds"],
#                     win_percentage=Decimal(str(s["winPercentage"])),
#                     place_percentage=Decimal(str(s["placePercentage"])),
#                     roi=Decimal(str(s["roi"])),
#                     ))

#         # ——— Bulk upsert with ignore_conflicts ———
#         JockeyStatistic.objects.bulk_create(
#             stats_jockey,
#             update_conflicts=True,
#             update_fields=[
#                 "runs", "wins", "seconds", "thirds",
#                 "win_percentage", "place_percentage", "roi"
#             ],
#             unique_fields=["jockey", "category", "value", "track", "trainer"],
#         )

#         print(f"Successfully synced statistics for: {jockey['name']} (ID: {jockeyId})")




# # 4. Advanced trainer statistics api
# def sync_trainer_details(trainerId: int):
#     url = f'{BASE_URL}/horse-racing/v1/statistics/trainer/{trainerId}'
#     headers = {"Authorization": f"Bearer {settings.FORMPRO_API_KEY}",
#                "Accept": "application/json"}

#     try:
#         req= requests.get(url, headers=headers)
#         req.raise_for_status()
#     except Exception as e:
#         print(f"Failed to fetch trainer details: {e}")
#         return False

#     data = req.json()
#     if data:
#         trainer_data = data['trainer']
#         trainer_Statistics = data['trainerStatistics']

#         # create and update the records for the trainer
#         trainer_obj, _ = Trainer.objects.update_or_create(
#             trainer_id=trainer_data['trainerId'],
#             defaults={
#                 'name': trainer_data['name'],
#                 'last_win': trainer_Statistics.get('lastWin'),
#                 'total_prize_money': trainer_Statistics.get('totalPrizeMoney'),
#                 'average_prize_money': trainer_Statistics.get('averagePrizeMoney'),
#             }
#         )

#         # create and update the records for the trainer statistics
#         trainer_stats = []

#         # create the function for uploading the data 
#         def add_trainer_stats(category, items, value, track=None, jockey=None, custom_value=None):
#             for item in items:
#                 s = item['statistics']
#                 value = custom_value or (item.get(value) if value else "Overall")

#                 trainer_stats.append(TrainerStatistic(
#                     trainer = trainer_obj,
#                     category = category,
#                     value = value,
#                     track = track,
#                     jockey = jockey,
#                     runs = s['runs'],
#                     wins = s['wins'],
#                     seconds = s['seconds'],
#                     thirds = s['thirds'],
#                     win_percentage = Decimal(str(s['winPercentage'])),
#                     place_percentage = Decimal(str(s['placePercentage'])),
#                     roi = Decimal(str(s['roi'])),
#                 ))


#         # ------trainer12MonthsDistanceStatistics----------
#         add_trainer_stats("distance", data.get("trainer12MonthsDistanceStatistics", []), "distance")

#         # ------trainer12MonthsGroupRaceStatistics----------
#         add_trainer_stats("groupRace", data.get("trainer12MonthsGroupRaceStatistics", []), "groupRace")

#         #-------trainer12MonthsResumingStatistics----------
#         add_trainer_stats("resuming", data.get("trainer12MonthsResumingStatistics", []), "resuming")

#         #-------trainer12MonthsTrackStatistics----------
#         for item in data.get("trainer12MonthsTrackStatistics", []):
#                 track_data = item["track"]
#                 track_obj, _ = Track.objects.get_or_create(
#                     trackId=track_data["trackId"],
#                     defaults={"name": track_data["name"], "countryIso2": track_data.get("countryIso2", "AU")}
#                 )
#                 add_trainer_stats(
#                 category="track",
#                 items=[item],
#                 track=track_obj,
#                 custom_value=track_data["name"] 
#             )

#         # ------trainer12MonthsJockeyStatistics----------
#         # add_trainer_stats("jockey", data.get("trainer12MonthsJockeyStatistics", []), "jockey")
#         for item in data.get("trainer12MonthsJockeyStatistics", []):
#                 jockey_data = item["jockey"]
#                 jockey_obj, _ = Jockey.objects.get_or_create(
#                     jockeyId=jockey_data["jockeyId"],
#                     defaults={"name": jockey_data["name"]}
#                 )
#                 add_trainer_stats(
#                 category="jockey",
#                 items=[item],
#                 jockey=jockey_obj,
#                 custom_value=jockey_data["name"]  
#             )
                
#         # ——— Period Stats (12Months, lastTen, asFavourite, etc.) ———
#         period_mapping = {
#             "12Months": "Last 12 Months",
#             "lastTen": "Last 10 Starts",
#             "season": "This Season",
#             "asFavourite": "As Favourite",
#             "night": "Night Racing",
#             "career": "Career",
#         }
#         for key, label in period_mapping.items():
#             if key in trainer_Statistics and trainer_Statistics[key]:
#                 s = trainer_Statistics[key]
#                 trainer_stats.append(TrainerStatistic(
#                     trainer=trainer_obj,
#                     category="period",
#                     value=label,
#                     track=None,
#                     runs=s["runs"],
#                     wins=s["wins"],
#                     seconds=s["seconds"],
#                     thirds=s["thirds"],
#                     win_percentage=Decimal(str(s["winPercentage"])),
#                     place_percentage=Decimal(str(s["placePercentage"])),
#                     roi=Decimal(str(s["roi"])),
#                     ))

#         # ——— Bulk upsert with ignore_conflicts ———
#         TrainerStatistic.objects.bulk_create(
#             trainer_stats,
#             update_conflicts=True,
#             update_fields=[
#                 "runs", "wins", "seconds", "thirds",
#                 "win_percentage", "place_percentage", "roi"
#             ],
#             unique_fields=["trainer", "category", "value", "track", "jockey"],
#         )

#         print(f"Successfully synced statistics for: {trainer_data['name']} (ID: {trainerId})")



# # 5.prediction (/horse-racing/v1/predictor/meeting/{meetingId})
# def sync_prediction(meetingId):
#     url = f"{BASE_URL}/horse-racing/v1/predictor/meeting/{meetingId}"
#     headers = {"Authorization": f"Bearer {settings.FORMPRO_API_KEY}",
#                "Accept": "application/json"}
    
#     try:
#         req= requests.get(url, headers=headers)
#         req.raise_for_status()
#     except Exception as e:
#         print(f"Error fetching prediction data: {e}")
#         return

#     data = req.json()
#     ratings_to_save = []
#     if data:
#         with transaction.atomic():
#             for race_wrapper in data["races"]: 
#                 for sel_wrapper in race_wrapper.get("selections", []):
#                     sel_data = sel_wrapper["selection"]
#                     selection_id = sel_data["selectionId"]

#                     try:
#                         selection_obj = Selection.objects.get(selectionId=selection_id)
#                     except Exception as e:
#                         print(f"Error fetching selection data: {e}")
#                         continue
   
#                     # Loop through ALL predictor ratings (BALANCED, WET_TRACK, etc.)
#                     for rating in sel_wrapper.get("predictorRatings", []):
#                         preset_id = rating["presetId"]
#                         preset_name = rating["presetName"]
#                         norm_rating = Decimal(str(rating["normalisedRating"]))

#                         # Get or create the Preset
#                         preset_obj, _ = PredictorPreset.objects.get_or_create(
#                             preset_id=preset_id,
#                             defaults={"name": preset_name}
#                         )

#                         ratings_to_save.append(PredictorRating(
#                             selection=selection_obj,
#                             preset=preset_obj,
#                             normalised_rating=norm_rating,
#                             rating_100=int(round(norm_rating * 100))  # ← your genius field
#                         ))

#             PredictorRating.objects.bulk_create(
#             ratings_to_save,
#             update_conflicts=True,
#             update_fields=["normalised_rating", "rating_100"],
#             unique_fields=["selection", "preset"]
#         )

#     print(f"Success: Synced {len(ratings_to_save)} predictor ratings for meeting {meetingId}")
#     return True



# # 6. Field (/horse-racing/v1/field/meeting/{meetingId})
# def sync_field_for_meeting(meetingId):
#     url = f"https://api.formpro.com.au/horse-racing/v1/field/meeting/{meetingId}"
#     headers = {
#         "Authorization": f"Bearer {settings.FORMPRO_API_KEY}",
#         "Accept": "application/json"
#     }

#     try:
#         response = requests.get(url, headers=headers, timeout=30)
#         response.raise_for_status()
#     except Exception as e:
#         print(f"Error fetching field data for meeting {meetingId}: {e}")
#         return False

#     data = response.json()
#     meeting_data = data.get("meeting")
#     if not meeting_data:
#         print("No meeting data returned")
#         return False

#     track_data = meeting_data.get("track")
#     races_data = data.get("races", [])

#     # 1. Update Meeting + Track (with extra field data)
#     meeting_obj, _ = Meeting.objects.update_or_create(
#         meetingId=meeting_data["meetingId"],
#         defaults={
#             "name": meeting_data.get("name"),
#             "category": meeting_data.get("category"),
#             "meeting_type": meeting_data.get("type"),  # Note: API uses "type", not "meetingType"
#             "rail_position": meeting_data.get("railPosition"),
#             "time_slot": meeting_data.get("timeSlot"),
#             "weather_condition": meeting_data.get("weatherCondition"),
#             "temperature": meeting_data.get("temperature"),
#             "tab_status": meeting_data.get("tabStatus", False),
#         }
#     )

#     track_obj, _ = Track.objects.update_or_create(
#         trackId=track_data["trackId"],
#         defaults={
#             "name": track_data["name"],
#             "countryIso2": track_data["countryIso2"],
#             "address": track_data.get("address"),
#             "circumference": track_data.get("circumference"),
#             "straight": track_data.get("straight"),
#             "is_clockwise": track_data.get("isClockwise"),
#             "sprint_lane": track_data.get("sprintLane", False),
#             "surface": track_data.get("surface"),
#             "track_code": track_data.get("trackCode"),
#         }
#     )

#     # Ensure meeting has correct track
#     meeting_obj.track = track_obj
#     meeting_obj.save()

#     # Prepare lists for bulk operations
#     races_to_create = []
#     selections_to_create = []
#     horses_to_update = []
#     jockeys_to_update = []
#     trainers_to_update = []

#     # Cache for objects to avoid duplicates in this sync
#     horse_cache = {}
#     jockey_cache = {}
#     trainer_cache = {}

#     for race_wrapper in races_data:
#         race_info = race_wrapper.get("race")
#         if not race_info:
#             continue

#         # Handle Race
#         race_defaults = {
#             "meeting": meeting_obj,
#             "number": race_info["number"],
#             "name": race_info.get("name", ""),
#             "distance": race_info.get("distance"),
#             "distance_units": race_info.get("distanceUnit"),
#             "prize_money": Decimal(str(race_info["prizeMoney"])) if race_info.get("prizeMoney") else None,
#             "start_type": race_info.get("startType"),
#             "startTimeUtc": race_info.get("startTimeUtc"),
#             "track_condition": race_info.get("trackConditionOverall"),
#             "track_condition_rating": race_info.get("trackConditionRating"),
#             "track_type": race_info.get("trackType"),
#             "entry_conditions": race_info.get("entryConditions", {}),
#             "isAbandoned": race_info.get("isAbandoned", False),
#         }

#         race_obj, created = Race.objects.update_or_create(
#             raceId=race_info["raceId"],
#             defaults=race_defaults
#         )

#         # Process all selections in this race
#         for sel_data in race_wrapper.get("selections", []):
#             horse_data = sel_data.get("horse", {})
#             jockey_data = sel_data.get("jockey", {})
#             trainer_data = sel_data.get("trainer", {})

#             horse_id = horse_data.get("horseId")
#             jockey_id = jockey_data.get("jockeyId")
#             trainer_id = trainer_data.get("trainerId")

#             # === Horse ===
#             if horse_id and horse_id not in horse_cache:
#                 horse_obj, _ = Horse.objects.update_or_create(
#                     horse_id=horse_id,
#                     defaults={
#                         "name": horse_data.get("name", ""),
#                         "age": horse_data.get("age"),
#                         "colour": horse_data.get("colour"),
#                         "sex": horse_data.get("sex"),
#                         "foal_date": horse_data.get("foalDate"),
#                         "sire": horse_data.get("sire"),
#                         "dam": horse_data.get("dam"),
#                         "damsire": horse_data.get("damsire"),
#                         "breeder": horse_data.get("breeder"),
#                         "owners": horse_data.get("owners"),
#                         "training_location": horse_data.get("trainingLocation"),
#                     }
#                 )
#                 horse_cache[horse_id] = horse_obj

#             # === Jockey ===
#             if jockey_id and jockey_id not in jockey_cache:
#                 jockey_obj, _ = Jockey.objects.update_or_create(
#                     jockey_id=jockey_id,
#                     defaults={
#                         "name": jockey_data.get("name", ""),
#                         "country": jockey_data.get("country"),
#                         "state": jockey_data.get("state"),
#                         "is_apprentice": jockey_data.get("isApprentice", False),
#                     }
#                 )
#                 jockey_cache[jockey_id] = jockey_obj

#             # === Trainer ===
#             if trainer_id and trainer_id not in trainer_cache:
#                 trainer_obj, _ = Trainer.objects.update_or_create(
#                     trainer_id=trainer_id,
#                     defaults={
#                         "name": trainer_data.get("name", ""),
#                         "location": trainer_data.get("location"),
#                         "postcode": trainer_data.get("postcode"),
#                         "state": trainer_data.get("state"),
#                         "title": trainer_data.get("title"),
#                     }
#                 )
#                 trainer_cache[trainer_id] = trainer_obj

#             # === Selection ===
#             selection_defaults = {
#                 "race": race_obj,
#                 "horse": horse_cache.get(horse_id),
#                 "jockey": jockey_cache.get(jockey_id),
#                 "trainer": trainer_cache.get(trainer_id),
#                 "number": sel_data.get("number"),
#                 "barrier": sel_data.get("barrier"),
#                 "weight": Decimal(str(sel_data["weight"])) if sel_data.get("weight") else None,
#                 "claim": sel_data.get("claim"),
#                 "handicap_rating": sel_data.get("handicapRating"),
#                 "gear": sel_data.get("gear"),
#                 "gear_changes": sel_data.get("gearChanges"),
#                 "racing_colours": sel_data.get("racingColours"),
#                 "silks_image": sel_data.get("silksImage"),
#                 "isScratched": sel_data.get("isScratched", False),
#                 "isEmergency": sel_data.get("isEmergency", False),
#             }

#             Selection.objects.update_or_create(
#                 selectionId=sel_data["selectionId"],
#                 defaults=selection_defaults
#             )

#     print(f"Successfully synced field data for meeting {meetingId}")
#     return True


# # 7./horse-racing/v1/form/race/{raceId}
# @transaction.atomic
# @transaction.atomic
# def sync_meeting_results(meetingId: int):
#     url = f"https://api.formpro.com.au/horse-racing/v1/results/final/meeting/{meetingId}"
#     headers = {"Authorization": f"Bearer {settings.FORMPRO_API_KEY}"}

#     try:
#         resp = requests.get(url, headers=headers, timeout=60)
#         resp.raise_for_status()
#     except Exception as e:
#         print(f"[ERROR] Meeting {meetingId}: {e}")
#         return False

#     data = resp.json()
#     meeting_data = data["meeting"]

#     # 1. Ensure Meeting + Track
#     track, _ = Track.objects.update_or_create(
#         trackId=meeting_data["track"]["trackId"],
#         defaults={"name": meeting_data["track"]["name"], "countryIso2": "AU"}
#     )
#     meeting, _ = Meeting.objects.update_or_create(
#         meetingId=meetingId,
#         defaults={
#             "date": meeting_data["date"],
#             "track": track,
#             "stage": "Results",
#             "isTrial": meeting_data.get("isTrial", False),
#         }
#     )

#     # Containers for bulk operations
#     races_to_update = []
#     selections_to_create = []
#     selections_to_update = []
#     history_to_create = []
#     history_to_update = []

#     # Caches
#     horse_cache = {}
#     jockey_cache = {}
#     trainer_cache = {}  # ← Fixed: was using jockey_cache!

#     print(f"[INFO] Syncing {len(data.get('races', []))} races for meeting {meetingId}")

#     for race_entry in data.get("races", []):
#         race_result = race_entry["raceResult"]
#         selections_data = race_entry.get("selectionResults", [])

#         race_id = race_result["raceId"]

#         # Update Race
#         race, created = Race.objects.get_or_create(raceId=race_id)
#         race.meeting = meeting
#         race.number = race_result["number"]
#         race.name = race_result.get("name", "")
#         # race.official_time = _parse_time(race_result.get("officialTime"))
#         # race.last_600_time = _parse_time(race_result.get("last600Time"))
#         race.race_starters = race_result.get("raceStarters")
#         # race.isAbandoned = race_result.get("isAbandoned", False)
#         # race.stage = "Results"
#         races_to_update.append(race)

#         winner_sel = second_sel = third_sel = None

#         # Pre-fetch existing selections and history
#         existing_sels = Selection.objects.filter(race=race).in_bulk(field_name="selectionId")
#         existing_histories = {
#             (h.horse_id, h.race_id): h
#             for h in HorseRaceHistory.objects.filter(race=race).select_related('horse')
#         }

#         for sel_data in selections_data:
#             if sel_data.get("isScratched"):
#                 continue

#             # Horse
#             horse_id = sel_data["horse"]["horseId"]
#             if horse_id not in horse_cache:
#                 horse, _ = Horse.objects.get_or_create(
#                     horse_id=horse_id,
#                     defaults={"name": sel_data["horse"]["name"]}
#                 )
#                 horse_cache[horse_id] = horse
#             horse = horse_cache[horse_id]

#             # Jockey
#             jockey = None
#             if sel_data.get("jockey"):
#                 jid = sel_data["jockey"]["jockeyId"]
#                 if jid not in jockey_cache:
#                     jockey, _ = Jockey.objects.get_or_create(
#                         jockey_id=jid,
#                         defaults={"name": sel_data["jockey"].get("name", "Unknown")}
#                     )
#                     jockey_cache[jid] = jockey
#                 jockey = jockey_cache[jid]

            
#             trainer = None
#             if sel_data.get("trainer"):
#                 tid = sel_data["trainer"]["trainerId"]
#                 if tid not in trainer_cache:
#                     trainer, _ = Trainer.objects.get_or_create(
#                         trainer_id=tid,
#                         defaults={"name": sel_data["trainer"].get("name", "Unknown")}
#                     )
#                     trainer_cache[tid] = trainer
#                 trainer = trainer_cache[tid]

#             sel_id = sel_data["selectionId"]
#             pos = sel_data.get("result")

#             # Selection fields
#             selection_fields = {
#                 "race": race,
#                 "horse": horse,
#                 "jockey": jockey,
#                 "trainer": trainer,
#                 "number": sel_data.get("number"),
#                 "barrier": sel_data.get("barrier"),
#                 "weight_carried": sel_data.get("weightCarried"),
#                 "starting_price": sel_data.get("startingPrice"),
#                 "result_position": pos,
#                 "margin_decimal": sel_data.get("marginDecimal"),
#                 "in_running_positions": sel_data.get("inRunning", []),
#                 "isScratched": False,
#             }

#             if sel_id in existing_sels:
#                 sel_obj = existing_sels[sel_id]
#                 for k, v in selection_fields.items():
#                     setattr(sel_obj, k, v)
#                 selections_to_update.append(sel_obj)
#             else:
#                 sel_obj = Selection(selectionId=sel_id, **selection_fields)
#                 selections_to_create.append(sel_obj)

#             # Capture placings
#             if pos == 1:
#                 winner_sel = sel_obj
#             elif pos == 2:
#                 second_sel = sel_obj
#             elif pos == 3:
#                 third_sel = sel_obj

#             # HorseRaceHistory
#             # history_key = (horse.horse_id, race.raceId)
#             # if history_key not in existing_histories:
#             #     history_to_create.append(
#             #         HorseRaceHistory(
#             #             horse=horse, race=race, selection=sel_obj,
#             #             finish_position=pos,
#             #             margin=sel_data.get("marginDecimal"),
#             #             starting_price=sel_data.get("startingPrice"),
#             #             in_running=sel_data.get("inRunning", []),
#             #             is_trial=meeting.isTrial
#             #         )
#             #     )
#             # else:
#             #     hist = existing_histories[history_key]
#             #     hist.selection = sel_obj
#             #     hist.finish_position = pos
#             #     hist.margin = sel_data.get("marginDecimal")
#             #     hist.starting_price = sel_data.get("startingPrice")
#             #     hist.in_running = sel_data.get("inRunning", [])
#             #     history_to_update.append(hist)

#         # Set placings on race
#         if winner_sel:
#             race.winner = winner_sel
#             race.winner_horse = winner_sel.horse
#             race.winner_jockey = winner_sel.jockey
#         if second_sel:
#             race.second = second_sel
#         if third_sel:
#             race.third = third_sel

#     # BULK OPERATIONS
#     if races_to_update:
#         Race.objects.bulk_update(
#             races_to_update,
#             fields=[
#                 "meeting", "number", "name", "official_time", "last_600_time",
#                 "race_starters", "isAbandoned", "stage",
#                 "winner", "winner_horse", "winner_jockey", "second", "third"
#             ]
#         )

#     if selections_to_create:
#         Selection.objects.bulk_create(selections_to_create, ignore_conflicts=True)
#     if selections_to_update:
#         Selection.objects.bulk_update(
#             selections_to_update,
#             fields=[
#                 "horse", "jockey", "trainer", "number", "barrier", "weight_carried",
#                 "starting_price", "result_position", "margin_decimal",
#                 "in_running_positions", "isScratched"
#             ]
#         )

#     # if history_to_create:
#     #     HorseRaceHistory.objects.bulk_create(history_to_create, ignore_conflicts=True)
#     # if history_to_update:
#     #     HorseRaceHistory.objects.bulk_update(
#     #         history_to_update,
#     #         fields=["selection", "finish_position", "margin", "starting_price", "in_running"]
#     #     )

#     print(f"[SUCCESS] Meeting {meetingId} synced with bulk operations")
#     return True










        
                
                


           


           








       








            









    
    
                
