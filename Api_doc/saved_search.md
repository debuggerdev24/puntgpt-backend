1. Saved Search API: 
The Saved Search API allows authenticated users to save, view, update, and delete search filters for reuse.The number of saved searches and allowed filters depend on the user’s subscription plan.

2. Authentication (Required for all endpoints)
    Header
    Authorization: Bearer <access_token>

API ENDPOINTS: 

1. List Saved Searches
    => Endpoint: GET /saved-search/
    => Purpose : Fetch all saved searches for the authenticated user, ordered by most recently updated.
    => Request Format: No query parameters, No request body
    => Sample response: 

        Success Response
        HTTP Status

        200 OK

        Example Response
        {
        "success": true,
        "message": "Saved searches fetched successfully.",
        "data": [
            {
            "id": 5,
            "name": "Today Randwick Runners",
            "filters": {
                "jump": "jumps_today",
                "track": "Randwick",
                "placed_last_start": true
            },
            "created_at": "2026-01-01T10:15:00Z",
            "updated_at": "2026-01-04T08:20:00Z"
            }
        ]
        }

        Error Responses
        401 – Unauthorized
        {
        "success": false,
        "message": "Authentication credentials were not provided."
        }

        500 – Server Error
        {
        "success": false,
        "message": "Failed to fetch saved searches.",
        "errors": {
            "detail": "Internal server error"
        }
        }

2. Create a Saved Search
    => Endpoint: POST /saved-search/
    => Request Format: Data is sent in the request body
    => Content-Type: application/json
    => Request Body Fields
        * name : A human-friendly label for the saved search.

            Type: string
            Required: Yes
            Format: Non-empty text
            Example: "Morning Pro Picks"


        * filters: Stores the exact filters that will later be applied to the Upcoming Runners API.

            Type: object
            Required: Yes
            Default: None
            Example:
                {
                "jump": "jumps_today",
                "track": "Randwick",
                "won_last_start": true
                }

            sample response:           
                Success Response
                HTTP Status

                201 Created

                Example Response
                {
                "success": true,
                "message": "Search saved successfully.",
                "data": {
                    "id": 8,
                    "name": "Pro Barrier Picks",
                    "filters": {
                    "jump": "jumps_tomorrow",
                    "barrier": "5",
                    "won_last_12_months": true
                    },
                    "created_at": "2026-01-05T07:30:00Z",
                    "updated_at": "2026-01-05T07:30:00Z"
                }
                }

                Error Responses
                400 – Invalid Data
                {
                "success": false,
                "message": "Invalid data.",
                "errors": {
                    "filters": [
                    "These filters are not allowed on your plan: won_last_start"
                    ]
                }
                }

                403 – Free Plan Limit Reached
                {
                "success": false,
                "message": "Upgrade to Pro Punter to save more than 3 searches."
                }

                400 – No Subscription
                {
                "success": false,
                "message": "User does not have a subscription."
                }


3. Get a Single Saved Search

    => Endpoint: GET /saved-search/{id}/
    => Path Parameter: id (Unique identifier of the saved search.)
        Type: number (integer)
        Required: Yes
        Example: 8

    => Sample response: 
            Success Response
            HTTP Status

            200 OK

            {
            "success": true,
            "message": "Search fetched successfully.",
            "data": {
                "id": 8,
                "name": "Pro Barrier Picks",
                "filters": {
                "jump": "jumps_tomorrow",
                "barrier": "5"
                },
                "created_at": "2026-01-05T07:30:00Z",
                "updated_at": "2026-01-05T07:30:00Z"
            }
            }

            Error Response
            404 – Not Found
            {
            "success": false,
            "message": "Search not found."
            }

4. Update a Saved Search (Partial Update)
    => Endpoint:PATCH /saved-search/{id}/
    => Request Format: Request body (JSON)
        Fields are optional, should be same as that in allowed filter

    => Response:
            200 OK

            {
            "success": true,
            "message": "Search updated successfully.",
            "data": {
                "id": 8,
                "name": "Updated Search Name",
                "filters": {
                "jump": "jumps_today"
                },
                "created_at": "2026-01-05T07:30:00Z",
                "updated_at": "2026-01-05T09:10:00Z"
            }
            }

            Error Responses

            400 – Invalid filters or name

            404 – Search not found

5. Delete a Saved Search
    => Endpoint: DELETE /saved-search/{id}/
    => Response: 

        Success Response
        HTTP Status

        204 No Content

        {
        "success": true,
        "message": "Search deleted successfully."
        }

        Error Response
        404 – Not Found
        {
        "success": false,
        "message": "Search not found."
        }
