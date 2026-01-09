from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.utils.response import success_response, error_response
from datetime import datetime, timedelta
from django.utils import timezone
import pytz
from horse_race.models.selection import Selection
from subscription.models import UserSubscription
from horse_race.models.horse import HorseStatistic
from django.db.models import OuterRef, Exists, Subquery, Q, IntegerField, F
from horse_race.models.jockey_horse_static import JockeyHorseStatistic

def time_conversion(time):
    try: 
        australia = pytz.timezone("Australia/Sydney")
        current_time_str = time 

        if current_time_str.endswith("Z"):
            current_time = datetime.strptime(current_time_str[:-1], "%Y-%m-%dT%H:%M:%S%z")
        else:
            current_time = datetime.strptime(current_time_str, "%Y-%m-%dT%H:%M:%S")

        # Convert the datetime object to the Australia/Sydney timezone
        current_time_in_sydney = current_time.astimezone(australia)

        # Format the time in AM/PM format
        formatted_time = current_time_in_sydney.strftime("%Y-%m-%d %I:%M:%S %p")

        return formatted_time
    except Exception as e:
        return None


def format_results(results):
    return [
        {
            "selection_id": r["selectionId"],
            "horse_number": r["number"],
            "horse_name": r["horse__name"],
            "jockey_name": r["jockey__name"],
            "trainer_name": r["trainer__name"],
            "track": r["race__meeting__track__name"],
            "race_number": r["race__number"],
            "jump_time_au": time_conversion(r["race__startTimeUtc_raw"]),
            "silks_image": r["silks_image"],
            "odds": r["playup_fixed_odds_win"],
        }
        for r in results
    ]


class UpcomingRunnersView(APIView):  
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try: 

            # Check the user's subscription:
            #       - Allow "Pro Punters" to use all filters
            #       - Restrict "Mug Punters" to only some filters

            user = request.user
            subscription = UserSubscription.objects.filter(user=user).first()
            current_subscription = subscription.plan.plan if subscription else None

            if current_subscription == "Free ‘Mug Punter’ Account":
                allowed_filters = [
                    "jump","track", "placed_last_start", "placed_at_distance", "placed_at_track", "odds_range"]
            else:
                allowed_filters = [
                    "jump","track", "placed_last_start", "placed_at_distance", "placed_at_track", "odds_range",
                    "wins_at_track", "win_at_distance", "won_last_start", "won_last_12_months",
                    "jockey_horse_wins","jockey_strike_rate_last_12_months", "barrier"
                ]

            # get the jump filter
            jump = request.query_params.get("jump", "jumps_today")
            
            if jump not in ["jumps_within_10mins","jumps_within_an_hour", "jumps_today", "jumps_tomorrow"]: 
                response, code = error_response(
                    "Invalid jump filter.",
                    errors={"jump": ["Invalid jump filter."]},
                    status_code=status.HTTP_400_BAD_REQUEST
                )
                return Response(response, status=code)
                  
            # other filter criteria that based on the subscription:

            # Mug Punter filter criteria 
            track = request.query_params.get("track")
            placed_last_start = request.query_params.get("placed_last_start")
            placed_at_distance = request.query_params.get("placed_at_distance")
            placed_at_track = request.query_params.get("placed_at_track")
            odds_range = request.query_params.get("odds_range")
            
            # pro punter filter criteria (+ the mug punter filter criteria)
            wins_at_track = request.query_params.get("wins_at_track")
            win_at_distance = request.query_params.get("win_at_distance")
            won_last_start = request.query_params.get("won_last_start")
            won_last_12_months = request.query_params.get("won_last_12_months")
            jockey_horse_wins = request.query_params.get("jockey_horse_wins")
            jockey_strike_rate_last_12_months = request.query_params.get("jockey_strike_rate_last_12_months")
            barrier = request.query_params.get("barrier")


            filter_applied = set(request.query_params.keys())
            invalid_filter_applied = filter_applied - set(allowed_filters)

            if invalid_filter_applied:
                response, code = error_response(
                    "Invalid filter.",
                    errors={"filter": [f"Invalid filter applied in the request.{invalid_filter_applied}"]},
                    status_code=status.HTTP_400_BAD_REQUEST
                )
                return Response(response, status=code)
            
                       
            # fetching the date and time 
            australia_tz = pytz.timezone('Australia/Sydney')
            now_au = timezone.now().astimezone(australia_tz)
            today_date = now_au.date()
            tomorrow_date = today_date + timedelta(days=1)

            # base query
            base_qu = Selection.objects.select_related(
                    "horse",
                    "jockey",
                    "trainer",
                    "race__meeting",
                    "race__meeting__track"
                ).values(
                    "selectionId",
                    "number",
                    "horse__name",
                    "jockey__name",
                    "trainer__name",
                    "race__number",
                    "race__startTimeUtc",
                    "race__startTimeUtc_raw",
                    "race__meeting__track__name",
                    "silks_image",
                    "playup_fixed_odds_win"
                )

            # logic for jumps within 10mins and Jumps within an hour
            if jump in ["jumps_within_10mins", "jumps_within_an_hour"]:

                minutes = 10 if jump == "jumps_within_10mins" else 60
    
                results = base_qu.filter(
                    race__startTimeUtc__gte=now_au,  
                    race__startTimeUtc__lte=now_au + timedelta(minutes=minutes)
                )

            # logic for jumps today
            elif jump == "jumps_today":
                results = base_qu.filter(race__meeting__date=today_date)

            # logic for jumps tomorrow
            else:
                results = base_qu.filter(race__meeting__date=tomorrow_date)


            # filtering based on the result basis

            # track basis: filter results by the specified track
            '''
            Filter the results to include only selections where the race was run
            at the specified track. The track name is matched case-insensitively
            against the race meeting's track name.
            '''
            
            if track:
                results = results.filter(race__meeting__track__name__iexact=track)


            # placed last start: indicates whether the horse recorded any finishing position in its most recent race
            '''
            Determine whether the selected horse has a recorded result position
            in its most recent start.

            Due to incomplete data from the Form API, some selections do not have a recorded
            result position. The API reliably provides finishing positions for the first
            three runners, which are recorded correctly, while finishing positions for
            other runners may be missing.
            '''

            if placed_last_start:
                last_selection_qs = Selection.objects.filter(
                    horse=OuterRef("horse"),
                    race__startTimeUtc__lt=timezone.now(),
                ).order_by("-race__startTimeUtc")

                last_result_position_subquery = Subquery(
                    last_selection_qs.values('result_position')[:1],
                    output_field=IntegerField()
                )

                results = results.annotate(
                    last_result_position=last_result_position_subquery
                ).filter(last_result_position__isnull=False)
                

            # placed at distance: wheather this horse was placed at distance or not
            '''
            Determine whether the selected horse has at least one placement at the specified distance.
            This requires looking up the horse's statistics table and checking the
            "distance" category for the given distance value with runs greater than zero. Orelse we can use place percentage and better to stick in run 
            '''
            
            if placed_at_distance:
                value = placed_at_distance
                print(f"value: {value}")
                if value == "0 - 1000m":
                    value = "'0 - 1000m'"
                results = results.filter(
                    Exists(
                        HorseStatistic.objects.filter(
                            horse=OuterRef("horse"),
                            category="distance",
                            value=value,
                            runs__gt=0
                        )
                    )
                )   

            # placed at track: wheather this horse was placed at track or not
            '''
            Determine whether the selected horse has at least one placement at the specified track.
            This requires looking up the horse's statistics table and checking the
            "track" category for the given track value with runs greater than zero.
            '''
            if placed_at_track:
                results = results.filter(
                    Exists(
                        HorseStatistic.objects.filter(
                            horse=OuterRef("horse"),
                            category="track",
                            value=placed_at_track,
                            runs__gt=0
                        )
                    )
                )

            # win at distance: indicates whether the horse has previously won at the given race distance
            '''
            Determine whether the selected horse has at least one win at the specified distance.
            This requires looking up the horse's statistics table and checking the
            "distance" category for the given distance value with wins greater than zero.

            '''

            if win_at_distance:
                results = results.filter(
                    Exists(
                        HorseStatistic.objects.filter(
                            horse=OuterRef("horse"),
                            category="distance",
                            value=win_at_distance,
                            wins__gt=0
                        )
                    )
                )


            # win at track: indicates whether the horse has previously won at the given track
            '''
            Determine whether the selected horse has at least one win at the specified track.
            This is done by checking the horse statistics table for the "track" category
            with the given track value and a win count greater than zero.
            '''
            if wins_at_track:
                results = results.filter(
                    Exists(
                        HorseStatistic.objects.filter(
                            horse=OuterRef("horse"),
                            category="track",
                            value=wins_at_track,
                            wins__gt=0
                        )
                    )
                )
                

            # won last 12 months: indicates whether the horse has recorded at least one win in the last 12 months
            '''
            Determine whether the selected horse has won any race within the past 12 months.
            This is verified by checking the horse statistics table for the "period" category
            with the value "Last 12 Months" and a win count greater than zero.
            '''
       
            if won_last_12_months:
                results = results.filter(
                    Exists(
                        HorseStatistic.objects.filter(
                            horse=OuterRef("horse"),
                            category="period",
                            value="Last 12 Months",
                            wins__gt=0
                        )
                    )
                )

            # won last start: indicates whether the horse won its most recent race
            '''
            Determine whether the selected horse won its last start.
            The most recent past race for the horse is identified from the Selection model
            by ordering races by start time in descending order.
            If the result_position of that latest selection is 1, the horse is considered
            to have won its last start.
            '''

            if won_last_start:
                last_selection_qs = Selection.objects.filter(
                    horse=OuterRef("horse"),
                    race__startTimeUtc__lt=timezone.now(),
                ).order_by("-race__startTimeUtc")

                last_result_position_subquery = Subquery(
                    last_selection_qs.values('result_position')[:1],
                    output_field=IntegerField()
                )

                results = results.annotate(
                    last_result_position=last_result_position_subquery
                ).filter(last_result_position=1)

            # odds range 
            '''
            Filter selections where the fixed win odds exactly match the provided value.
            '''
            if odds_range:
                try:
                    results = results.filter(playup_fixed_odds_win=float(odds_range))
                except (ValueError, TypeError):
                    pass

            # jockey_horse_wins: indicates whether the horse and jockey pair have recorded wins together
            '''
            Determine whether the specific Horse and Jockey pair scheduled for this race
            have previously won together.
            This checks the JockeyHorseStatistic model for records matching both the
            Selection's horse and jockey with a win count greater than zero.
            '''
            if jockey_horse_wins and str(jockey_horse_wins).isdigit():
                min_wins = int(jockey_horse_wins)
                results = results.filter(
                    Exists(
                        JockeyHorseStatistic.objects.filter(
                            horse=OuterRef("horse"),
                            jockey=OuterRef("jockey"),
                            wins__gte=min_wins
                        )
                    )
                )


            # jockey strike rate last 12 months
            '''
            As this values are not available from the API so we are removing this filter
            '''


            # Barrier range: Currently, the "Won at Barrier Range" is being considered for the filter criteria.
            
            '''
            Determine whether the selected horse has at least one win at the specified barrier range.
            This requires looking up the horse's statistics table and checking the
            "barrier" category for the given barier value with wins greater than zero.
            '''
            if barrier: 
                results = results.filter(
                        Exists(
                            HorseStatistic.objects.filter(
                                horse=OuterRef("horse"),
                                category="barrier",
                                value=barrier,
                                wins__gt=0
                            )
                        )
                    )
                

            runner_count = results.count()
    
            response, code = success_response(
                    "Upcoming runners fetched successfully.",
                    data={
                        "runner_count": runner_count,  
                        "runners": format_results(results)
                        },
                     status_code=status.HTTP_200_OK)

            return Response(response, status=code)
        
        except Exception as e:
            response, code = error_response(
                "An error occurred while fetching upcoming runners.",
                errors={"error": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response(response, status=code)
        



