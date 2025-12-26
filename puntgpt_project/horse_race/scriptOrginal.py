# Identifier Api
import requests
'''
 using the api:
 /horse-racing/v1/identifiers/meeting/{date}. so the endpoint will be GET https://api.formpro.com.au/horse-racing/v1/identifiers/meeting/2025-12-06
 fetch all the meetings on the date

 from here we will get the meeting id and  track id horse and jockey details there.
def sync_date(date_str):  # e.g. "2025-12-06"
    response = requests.get(f"https://api.formpro.com.au/horse-racing/v1/identifiers/meeting/{date_str}", 
                            headers={"Authorization": "Bearer ..."})
    data = response.json()  # list of meetings

    for meeting_data in data:
        meeting_obj, _ = Meeting.objects.update_or_create(
            meetingId=meeting_data["meeting"]["meetingId"],
            defaults={
                "date": meeting_data["meeting"]["date"],
                "track_id": meeting_data["meeting"]["track"]["trackId"],
                "isTrial": meeting_data["meeting"]["isTrial"],
                "stage": meeting_data["meeting"]["stage"],
                "startTimeUtc": meeting_data["meeting"]["startTimeUtc"],
            }
        )

        for race_wrapper in meeting_data["races"]:
            race_obj, _ = Race.objects.update_or_create(
                raceId=race_wrapper["race"]["raceId"],
                defaults={
                    "meeting": meeting_obj,
                    "number": race_wrapper["race"]["number"],
                    "isAbandoned": race_wrapper["race"].get("isAbandoned", False),
                    "stage": race_wrapper["race"]["stage"],
                }
            )

            for sel in race_wrapper["selections"]:
                # Ensure master records exist
                Horse.objects.get_or_create(horseId=sel["horse"]["horseId"], defaults={"name": sel["horse"]["name"]})
                Jockey.objects.get_or_create(jockeyId=sel["jockey"]["jockeyId"], defaults={"name": sel["jockey"]["name"]})
                Trainer.objects.get_or_create(trainerId=sel["trainer"]["trainerId"], defaults={"name": sel["trainer"]["name"]})

                Selection.objects.update_or_create(
                    selectionId=sel["selectionId"],
                    defaults={
                        "race": race_obj,
                        "horse_id": sel["horse"]["horseId"],
                        "jockey_id": sel["jockey"]["jockeyId"],
                        "trainer_id": sel["trainer"]["trainerId"],
                        "number": sel.get("number"),
                        "isScratched": sel.get("isScratched", False),
                    }
                )
'''


# script for fecthing the specific horse data
'''
 Endpoint: /horse-racing/v1/statistics/horse/{horseId}

# tasks.py  (or put in a management command: python manage.py sync_horse_stats 12345)

import requests
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

# Make sure you have these models already:
# Horse, Track, HorseStatistic   ← from the final version we built

def sync_horse_statistics(horse_id: int):
    url = f"https://api.formpro.com.au/horse-racing/v1/statistics/horse/{horse_id}"
    headers = {"Authorization": "Bearer YOUR_API_TOKEN_HERE"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"API error {response.status_code} for horse {horse_id}")
        return False

    data = response.json()

    with transaction.atomic():
        # 1. Update/Create the Horse master record
        horse_defaults = {
            "name": data["horse"]["name"],
            "last_win": data["horseStatistics"].get("lastWin"),
            "total_prize_money": data["horseStatistics"].get("totalPrizeMoney"),
            "average_prize_money": data["horseStatistics"].get("averagePrizeMoney"),
        }

        # Career summary
        career = data["horseStatistics"]["career"]
        horse_defaults.update({
            "career_runs": career["runs"],
            "career_wins": career["wins"],
            "career_places": career["wins"] + career["seconds"] + career["thirds"],
            "career_win_pct": Decimal(str(career["winPercentage"])),
            "career_place_pct": Decimal(str(career["placePercentage"])),
            "career_roi": Decimal(str(career["roi"])),
        })

        horse, created = Horse.objects.update_or_create(
            horse_id=data["horse"]["horseId"],
            defaults=horse_defaults
        )

        # 2. Delete all old stats for this horse (fresh sync)
        horse.statistics.all().delete()

        # Helper: save a stat row
        def save_stat(category: str, value: str, stats: dict, track=None):
            HorseStatistic.objects.create(
                horse=horse,
                category=category,
                value=str(value),
                track=track,
                runs=stats["runs"],
                wins=stats["wins"],
                seconds=stats["seconds"],
                thirds=stats["thirds"],
                win_percentage=Decimal(str(stats["winPercentage"])),
                place_percentage=Decimal(str(stats["placePercentage"])),
                roi=Decimal(str(stats["roi"])),
            )

        # === Categorized stats (arrays) ===
        for item in data.get("horseBarrierStatistics", []):
            save_stat("barrier", item["barrier"], item["statistics"])

        for item in data.get("horseDistanceStatistics", []):
            save_stat("distance", item["distanceRange"], item["statistics"])

        for item in data.get("horseFieldSizeStatistics", []):
            save_stat("field_size", item["fieldSize"], item["statistics"])

        for item in data.get("horseGroupRaceStatistics", []):
            save_stat("group_race", item["groupClass"], item["statistics"])

        for item in data.get("horseResumingStatistics", []):
            save_stat("resuming", item["resumingRun"], item["statistics"])

        for item in data.get("horseDirectionStatistics", []):
            save_stat("direction", item["raceDirection"], item["statistics"])

        for item in data.get("horseWeightStatistics", []):
            save_stat("weight", item["weight"], item["statistics"])

        # Track-specific
        for item in data.get("horseTrackStatistics", []):
            track_obj, _ = Track.objects.get_or_create(
                trackId=item["track"]["trackId"],
                defaults={
                    "name": item["track"]["name"],
                    "countryIso2": item["track"].get("countryIso2", "AU")
                }
            )
            save_stat("track", item["track"]["name"], item["statistics"], track=track_obj)

        for item in data.get("horseTrackConditionStatistics", []):
            save_stat("track_condition", item["trackCondition"], item["statistics"])

        for item in data.get("horseTrackSurfaceStatistics", []):
            save_stat("surface", item["trackSurface"], item["statistics"])

        # === Period / Summary stats (12Months, lastTen, asFavourite, etc.) ===
        periods = {
            "12Months": "Last 12 Months",
            "season": "Current Season",
            "lastTen": "Last 10 Starts",
            "asFavourite": "As Favourite",
            "night": "Night Racing",
        }

        for key, display in periods.items():
            block = data["horseStatistics"].get(key)
            if block and isinstance(block, dict):
                save_stat("period", display, block)

    print(f"Successfully synced: {horse.name} (ID: {horse.horse_id})")
    return True


# Example usage:
# sync_horse_statistics(816627)   # works with dummy data
# sync_horse_statistics(700123)   # works with real horses like Nature Strip
'''


'''
# tasks.py or management command
import requests
from decimal import Decimal
from django.db import transaction

def sync_jockey_statistics(jockey_id):
    url = f"https://api.formpro.com.au/horse-racing/v1/statistics/jockey/{jockey_id}"
    headers = {"Authorization": "Bearer YOUR_TOKEN"}

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return False

    data = resp.json()
    jockey_data = data["jockey"]

    with transaction.atomic():
        # 1. Create/Update Jockey
        jockey, _ = Jockey.objects.update_or_create(
            jockey_id=jockey_data["jockeyId"],
            defaults={
                "name": jockey_data["name"],
                "last_win": data["jockeyStatistics"].get("lastWin"),
                "total_prize_money": data["jockeyStatistics"].get("totalPrizeMoney"),
                "average_prize_money": data["jockeyStatistics"].get("averagePrizeMoney"),
            }
        )

        # 2. Clear old stats
        jockey.statistics.all().delete()

        # Helper function
        def save_stat(cat, value, stats, track=None, trainer=None):
            JockeyStatistic.objects.create(
                jockey=jockey,
                category=cat,
                value=str(value),
                track=track,
                trainer=trainer,
                runs=stats["runs"],
                wins=stats["wins"],
                seconds=stats["seconds"],
                thirds=stats["thirds"],
                win_percentage=Decimal(str(stats["winPercentage"])),
                place_percentage=Decimal(str(stats["placePercentage"])),
                roi=Decimal(str(stats["roi"])),
            )

        # === 12-Month Categories ===
        save_stat("barrier", item["barrier"], item["statistics"])
        for item in data.get("jockey12MonthsBarrierStatistics", []):
            save_stat("barrier", item["barrier"], item["statistics"])

        for item in data.get("jockey12MonthsDistanceStatistics", []):
            save_stat("distance", item["distanceRange"], item["statistics"])

        for item in data.get("jockey12MonthsFieldSizeStatistics", []):
            save_stat("field_size", item["fieldSize"], item["statistics"])

        for item in data.get("jockey12MonthsGroupRaceStatistics", []):
            save_stat("group_race", item["groupClass"], item["statistics"])

        for item in data.get("jockey12MonthsTrackConditionStatistics", []):
            save_stat("track_condition", item["trackCondition"], item["statistics"])

        for item in data.get("jockey12MonthsTrackStatistics", []):
            track_obj, _ = Track.objects.get_or_create(
                trackId=item["track"]["trackId"],
                defaults={"name": item["track"]["name"]}
            )
            save_stat("track", item["track"]["name"], item["statistics"], track=track_obj)

        for item in data.get("jockey12MonthsTrainerStatistics", []):
            trainer_obj, _ = Trainer.objects.get_or_create(
                trainerId=item["trainer"]["trainerId"],
                defaults={"name": item["trainer"]["name"]}
            )
            save_stat("trainer", item["trainer"]["name"], item["statistics"], trainer=trainer_obj)

        # === Summary periods ===
        periods = data["jockeyStatistics"]
        for key in ["12Months", "asFavourite", "lastTen", "season", "night"]:
            block = periods.get(key)
            if block and isinstance(block, dict):
                save_stat("period", key.replace("12Months", "Last 12 Months"), block)

    print(f"Synced jockey: {jockey.name}")
    return True
'''

'''
# tasks.py or management command

import requests
from decimal import Decimal
from django.db import transaction

def sync_trainer_statistics(trainer_id: int):
    url = f"https://api.formpro.com.au/horse-racing/v1/statistics/trainer/{trainer_id}"
    headers = {"Authorization": "Bearer YOUR_TOKEN_HERE"}

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed {resp.status_code} for trainer {trainer_id}")
        return False

    data = resp.json()

    with transaction.atomic():
        # 1. Create/Update Trainer master record
        trainer_defaults = {
            "name": data["trainer"]["name"],
            "last_win": data["trainerStatistics"].get("lastWin"),
            "total_prize_money": data["trainerStatistics"].get("totalPrizeMoney"),
            "average_prize_money": data["trainerStatistics"].get("averagePrizeMoney"),
        }

        trainer, _ = Trainer.objects.update_or_create(
            trainer_id=data["trainer"]["trainerId"],
            defaults=trainer_defaults
        )

        )

        # 2. Clear old stats
        trainer.statistics.all().delete()

        # Helper function
        def save_stat(cat, value, stats_dict, track=None, jockey=None):
            TrainerStatistic.objects.create(
                trainer=trainer,
                category=cat,
                value=str(value),
                track=track,
                jockey=jockey,
                runs=stats_dict["runs"],
                wins=stats_dict["wins"],
                seconds=stats_dict["seconds"],
                thirds=stats_dict["thirds"],
                win_percentage=Decimal(str(stats_dict["winPercentage"])),
                place_percentage=Decimal(str(stats_dict["placePercentage"])),
                roi=Decimal(str(stats_dict["roi"])),
            )

        # === 12-Month Categories ===
        for item in data.get("trainer12MonthsDistanceStatistics", []):
            save_stat("distance", item["distanceRange"], item["statistics"])

        for item in data.get("trainer12MonthsGroupRaceStatistics", []):
            save_stat("group_race", item["groupClass"], item["statistics"])

        for item in data.get("trainer12MonthsResumingStatistics", []):
            save_stat("resuming", item["resumingRun"], item["statistics"])

        for item in data.get("trainer12MonthsTrackStatistics", []):
            track_obj, _ = Track.objects.get_or_create(
                trackId=item["track"]["trackId"],
                defaults={"name": item["track"]["name"], "countryIso2": item["track"].get("countryIso2", "AU")}
            )
            save_stat("track", item["track"]["name"], item["statistics"], track=track_obj)

        for item in data.get("trainer12MonthsJockeyStatistics", []):
            jockey_obj, _ = Jockey.objects.get_or_create(
                jockey_id=item["jockey"]["jockeyId"],
                defaults={"name": item["jockey"]["name"]}
            )
            save_stat("jockey", item["jockey"]["name"], item["statistics"], jockey=jockey_obj)

        # === Period stats (12Months, lastTen, asFavourite, etc.) ===
        periods = {
            "12Months": "Last 12 Months",
            "season": "Current Season",
            "lastTen": "Last 10 Starts",
            "asFavourite": "As Favourite",
            "night": "Night Racing",
        }

        for key, label in periods.items():
            block = data["trainerStatistics"].get(key)
            if block and isinstance(block, dict):
                save_stat("period", label, block)

    print(f"Synced trainer: {trainer.name} (ID: {trainer.trainer_id})")
    return True
'''

'''
# tasks.py — FINAL VERSION (uses your perfect models)

def sync_field_for_meeting(meeting_id: int):
    url = f"https://api.formpro.com.au/horse-racing/v1/field/meeting/{meeting_id}"
    headers = {"Authorization": "Bearer YOUR_TOKEN"}
    
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Field API failed: {meeting_id}")
        return False

    data = resp.json()
    meeting_data = data["meeting"]

    with transaction.atomic():
        # 1. Update Meeting + Track
        track_data = meeting_data["track"]
        Track.objects.update_or_create(
            trackId=track_data["trackId"],
            defaults={
                "name": track_data["name"],
                "countryIso2": track_data["countryIso2"],
                "address": track_data.get("address", ""),
                "circumference": track_data.get("circumference"),
                "straight": track_data.get("straight"),
                "is_clockwise": track_data.get("isClockwise"),
                "sprint_lane": track_data.get("sprintLane", False),
                "surface": track_data.get("surface", ""),
            }
        )

        Meeting.objects.update_or_create(
            meetingId=meeting_id,
            defaults={
                "name": meeting_data.get("name", ""),
                "category": meeting_data.get("category", ""),
                "meeting_type": meeting_data.get("type", ""),
                "time_slot": meeting_data.get("timeSlot", ""),
                "rail_position": meeting_data.get("railPosition", ""),
                "weather_condition": meeting_data.get("weatherCondition", ""),
                "temperature": meeting_data.get("temperature"),
                "tab_status": meeting_data.get("tabStatus", False),
            }
        )

        # 2. Races & Selections
        for race_wrapper in data.get("races", []):
            race_data = race_wrapper["race"]
            
            Race.objects.update_or_create(
                raceId=race_data["raceId"],
                defaults={
                    "name": race_data.get("name", ""),
                    "distance": race_data.get("distance"),
                    "prize_money": race_data.get("prizeMoney"),
                    "track_condition": race_data.get("trackConditionOverall", ""),
                    "track_condition_rating": race_data.get("trackConditionRating"),
                    "entry_conditions": race_data.get("entryConditions", {}),
                    "startTimeUtc": race_data.get("startTimeUtc"),
                }
            )

            for sel in race_wrapper.get("selections", []):
                selection = Selection.objects.get(selectionId=sel["selectionId"])

                # Update Selection (runner field data)
                Selection.objects.filter(pk=selection.pk).update(
                    barrier=sel.get("barrier"),
                    weight=sel.get("weight"),
                    claim=sel.get("claim"),
                    handicap_rating=sel.get("handicapRating"),
                    gear_current=sel.get("gear", ""),
                    gear_changes=sel.get("gearChanges", ""),
                    racing_colours=sel.get("racingColours", ""),
                    silks_image=sel.get("silksImage", ""),
                    isEmergency=sel.get("isEmergency", False),
                )

                # Update Horse profile
                h = sel["horse"]
                Horse.objects.update_or_create(
                    horse_id=h["horseId"],
                    defaults={
                        "name": h["name"],
                        "colour": h.get("colour", ""),
                        "sex": h.get("sex", ""),
                        "age": h.get("age"),
                        "foal_date": h.get("foalDate"),
                        "sire": h.get("sire", ""),
                        "dam": h.get("dam", ""),
                        "damsire": h.get("damsire", ""),
                        "breeder": h.get("breeder", ""),
                        "owners": h.get("owners", ""),
                        "silks_image": h.get("silksImage", ""),
                        "training_location": h.get("trainingLocation", ""),
                    }
                )

                # Update Jockey & Trainer details
                if sel.get("jockey"):
                    Jockey.objects.update_or_create(
                        jockey_id=sel["jockey"]["jockeyId"],
                        defaults={
                            "name": sel["jockey"]["name"],
                            "state": sel["jockey"].get("state", ""),
                            "country": sel["jockey"].get("country", ""),
                            "is_apprentice": sel["jockey"].get("isApprentice", False),
                        }
                    )

                if sel.get("trainer"):
                    Trainer.objects.update_or_create(
                        trainer_id=sel["trainer"]["trainerId"],
                        defaults={
                            "name": sel["trainer"]["name"],
                            "location": sel["trainer"].get("location", ""),
                            "postcode": sel["trainer"].get("postcode", ""),
                            "state": sel["trainer"].get("state", ""),
                            "title": sel["trainer"].get("title", ""),
                        }
                    )

    print(f"Field API 100% synced — Meeting {meeting_id}")
    return True
'''
'''
try:
            form_data = api.get(f"/form/race/{race_id}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                self.stdout.write(self.style.ERROR(f"Race {race_id} not found in Form API"))
                return
            raise

        # 2. Get Results (only if race is finished)
        results_data = None
        try:
            results_data = api.get(f"/results/final/race/{race_id}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                self.stdout.write("Race not finished yet → only Form data will be saved")

        self.process_form_data(api, form_data, dry_run)
        if results_data:
            self.process_results_data(api, results_data, dry_run)

        self.stdout.write(self.style.SUCCESS(f"Race {race_id} synced successfully"))

    def process_form_data(self, api, data, dry_run):
        race_info = data.get("race", {})
        race_id = race_info["raceId"]

        race = Race.objects.filter(raceId=race_id).first()
        if not race:
            self.stdout.write(self.style.WARNING(f"Race {race_id} not in DB yet. Skipping form sync."))
            return

        for item in data.get("form", []):
            horse_data = item["horse"]
            horse = Horse.objects.get(horse_id=horse_data["horseId"])

            # Update last 10 starts + prize money
            stats = item.get("statistics", {})
            if not dry_run:
                horse.last_10_starts = stats.get("lastTenStarts", "")[:10]
                horse.total_prize_money = stats.get("totalPrizeMoney")
                horse.average_prize_money = stats.get("averagePrizeMoney")
                horse.save(update_fields=['last_10_starts', 'total_prize_money', 'average_prize_money'])

            # Save racing history
            for hist in item.get("history", []):
                self.save_horse_race_history(hist, horse, dry_run)

    def save_horse_race_history(self, hist_data, horse, dry_run):
        meeting_data = hist_data["meeting"]
        race_result = hist_data["raceResult"]
        sel_result = hist_data["selectionResult"]

        past_race = Race.objects.filter(raceId=race_result["raceId"]).first()
        if not past_race:
            return  # Race not in our DB yet

        defaults = {
            "finish_position": sel_result.get("result"),
            "margin": sel_result.get("marginDecimal"),
            "starting_price": sel_result.get("startingPrice"),
            "in_running": sel_result.get("inRunning", []),
            "is_trial": meeting_data.get("isTrial", False),
        }

        if not dry_run:
            HorseRaceHistory.objects.update_or_create(
                horse=horse,
                race=past_race,
                defaults=defaults
            )
Pythondef process_results_data(self, api, data, dry_run):
        race_result = data["raceResult"]
        race_id = race_result["raceId"]

        race = Race.objects.get(raceId=race_id)

        if not dry_run:
            # Update race result fields
            race.official_time = self.parse_time(race_result.get("officialTime"))
            race.last_600_time = self.parse_time(race_result.get("last600Time"))
            race.race_starters = race_result.get("raceStarters")
            race.is_abandoned = race_result.get("isAbandoned", False)
            race.save()

            # Set winner, second, third
            winner_horse_id = race_result.get("winnerHorse", {}).get("horseId")
            if winner_horse_id:
                winner_sel = Selection.objects.filter(race=race, horse__horse_id=winner_horse_id).first()
                if winner_sel:
                    race.winner = winner_sel

            second_horse_id = race_result.get("secondHorse", {}).get("horseId")
            if second_horse_id:
                second_sel = Selection.objects.filter(race=race, horse__horse_id=second_horse_id).first()
                if second_sel:
                    race.second = second_sel

            third_horse_id = race_result.get("thirdHorse", {}).get("horseId")
            if third_horse_id:
                third_sel = Selection.objects.filter(race=race, horse__horse_id=third_horse_id).first()
                if third_sel:
                    race.third = third_sel

            race.save()

        # Update each selection result
        for sel_data in data.get("selectionResults", []):
            self.update_selection_result(sel_data, race, dry_run)

    def update_selection_result(self, sel_data, race, dry_run):
        selection = Selection.objects.filter(
            race=race,
            selectionId=sel_data["selectionId"]
        ).first()

        if not selection:
            return

        if not dry_run:
            selection.result_position = sel_data.get("result")
            selection.result_label = sel_data.get("resultLabel", "")
            selection.margin_decimal = sel_data.get("marginDecimal")
            selection.starting_price = sel_data.get("startingPrice")
            selection.weight_carried = sel_data.get("weightCarried")
            selection.in_running_positions = sel_data.get("inRunning", [])
            selection.save()

    def parse_time(self, time_str):
        if not time_str:
            return None
        try:
            mins, secs = time_str.split(':')
            secs, hundredths = (secs.split('.') + ['0'])[:2]
            return timedelta(minutes=int(mins), seconds=int(float(secs)), microseconds=int(hundredths.ljust(6, '0')[:6]) * 100)
        except:
            return None
'''
'''
# tasks.py
import requests
from decimal import Decimal
from django.db import transaction

def sync_predictor_for_meeting(meeting_id: int):
    url = f"https://api.formpro.com.au/horse-racing/v1/predictor/meeting/{meeting_id}"
    params = {"includeScratched": "false", "includeAbandoned": "false"}
    headers = {"Authorization": "Bearer YOUR_TOKEN"}

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"Predictor failed for meeting {meeting_id}")
        return False

    data = resp.json()

    with transaction.atomic():
        for race_data in data.get("races", []):
            for sel_wrapper in race_data.get("selections", []):
                sel_data = sel_wrapper["selection"]

                # Get your existing Selection object
                selection = Selection.objects.get(selectionId=sel_data["selectionId"])

                # Clear old ratings
                selection.predictor_ratings.all().delete()

                # Save new ones
                for rating in sel_wrapper.get("predictorRatings", []):
                    preset = PredictorPreset.objects.get(preset_id=rating["presetId"])
                    rating_100 = int(round(rating["normalisedRating"] * 100))

                    PredictorRating.objects.create(
                        selection=selection,
                        preset=preset,
                        normalised_rating=Decimal(str(rating["normalisedRating"])),
                        rating_100=rating_100,
                    )

    print(f"Predictor synced: Meeting {meeting_id}")
    return True
'''



    
   
