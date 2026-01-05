1. Upcoming Runners API

Fetch a list of upcoming horse race runners with optional filters based on race timing, track, horse performance, and jockey statistics.Available filters depend on the user’s subscription plan.

2. Endpoint: GET /api/upcoming-runners/

3. Authentication : This endpoint requires authentication.

    Required Header
    Authorization: Bearer <access_token>


4. Request Data Format:

    => All data is sent via query parameters
    => No request body is used

5. Subscription-Based Access Rules

    => The available filters depend on the user’s subscription plan:
    => Free “Mug Punter” Account:
        allowed_filters = [
                    "jump","track", "placed_last_start", "placed_at_distance", "placed_at_track", "odds_range"]

    => allowed_filters = [
                    "jump","track", "placed_last_start", "placed_at_distance", "placed_at_track", "odds_range",
                    "wins_at_track", "win_at_distance", "won_last_start", "won_last_12_months",
                    "jockey_horse_wins","jockey_strike_rate_last_12_months", "barrier"
                ]


    => ❗ If a user applies a filter not allowed by their subscription, the request will fail with 400 Bad Request.



6. Query Parameters
1. jump

Type: string
Required: No
Default: jumps_today

Allowed Values:jumps_within_10mins, jumps_within_an_hour, jumps_today, jumps_tomorrow


2. track

Type: string
Required: No

Example:
Randwick

Business Meaning:
Returns only runners racing at the specified track.
Matching is case-insensitive.

3. placed_last_start

Type: boolean (presence-based)
Required: No

Accepted Format:

Any non-empty value enables the filter
(true, 1, yes, etc.)

Business Meaning:
Includes horses that have a recorded finishing position in their most recent race.

⚠️ Due to external data limitations, only top 3 finishers are always reliably recorded.

4. placed_at_distance

Type: string
Required: No

Example:
0 - 1200m

Use the values that displayed in the  distance display

Business Meaning:
Includes horses that have ever placed (finished in top positions) at the given race distance.

5. placed_at_track

Type: string
Required: No

Example:
Randwick

Business Meaning:
Includes horses that have ever placed at the specified track.

6. wins_at_track (Pro only)

Type: string
Required: No

Example:
Randwick

Business Meaning:
Includes horses that have won at least once at the specified track.

7. win_at_distance (Pro only)

Type: string
Required: No

Example:
1400m

Business Meaning:
Includes horses that have won at least once at the specified distance.

8. won_last_start (Pro only)

Type: boolean (presence-based)
Required: No

Accepted Format:

Any non-empty value enables the filter

Business Meaning:
Includes horses that won their most recent race.

9. won_last_12_months (Pro only)

Type: boolean (presence-based)
Required: No

Accepted Format:

Any non-empty value enables the filter

Business Meaning:
Includes horses that have won at least one race in the last 12 months.

10. jockey_horse_wins (Pro only)

Type: number (integer)
Required: No

Example:
2

Business Meaning:
Includes runners where the same jockey and horse combination has won at least the given number of races together.

11. barrier (Pro only)

Type: string
Required: No

Example: 1-2

Business Meaning:
Includes horses that have won from the specified barrier position.



Sample Response:

Success Response
HTTP Status

200 OK

Example Response
{
  "success": true,
  "message": "Upcoming runners fetched successfully.",
  "data": {
    "runner_count": 2,
    "runners": [
      {
        "selection_id": 12345,
        "horse_number": 4,
        "horse_name": "Thunder Strike",
        "jockey_name": "J. McDonald",
        "trainer_name": "Chris Waller",
        "track": "Randwick",
        "race_number": 6,
        "jump_time_db": "2026-01-05T03:20:00Z",
        "jump_time_au": "2026-01-05 02:20:00 PM",
        "silks_image": "https://example.com/silks.png"
      }
    ]
  }
}

Error Responses
400 – Invalid Filter
{
  "success": false,
  "message": "Invalid filter.",
  "errors": {
    "filter": [
      "Invalid filter applied in the request. {'wins_at_track'}"
    ]
  }
}

400 – Invalid Jump Value
{
  "success": false,
  "message": "Invalid jump filter.",
  "errors": {
    "jump": [
      "Invalid jump filter."
    ]
  }
}

401 – Unauthorized
{
  "success": false,
  "message": "Authentication credentials were not provided."
}

500 – Internal Server Error
{
  "success": false,
  "message": "An error occurred while fetching upcoming runners.",
  "errors": {
    "error": "Unexpected server error message"
  }
}
