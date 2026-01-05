from rest_framework import serializers
from horse_race.models.saved_search_model import SavedSearch
from subscription.models import UserSubscription

class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ['id', 'name', 'filters', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    ALLOWED_FILTERS = {
        "Free ‘Mug Punter’ Account": [
            "jump", "track", "placed_last_start", "placed_at_distance",
            "placed_at_track", "odds_range"
        ],

        "default": [ 
            "jump", "track", "placed_last_start", "placed_at_distance", "placed_at_track", "odds_range",
            "wins_at_track", "win_at_distance", "won_last_start", "won_last_12_months",
            "jockey_horse_wins", "jockey_strike_rate_last_12_months", "barrier"
        ]
    }

    def get_allowed_filters(self, user):
        try:
            subscription = UserSubscription.objects.get(user=user)
            plan_name = subscription.plan.plan
            return self.ALLOWED_FILTERS.get(plan_name, self.ALLOWED_FILTERS["default"])
        except UserSubscription.DoesNotExist:
            return self.ALLOWED_FILTERS["default"]
        
    def validate_filters(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Filters must be a dictionary.")

        user = self.context['request'].user
        allowed = self.get_allowed_filters(user)
        invalid_keys = set(value.keys()) - set(allowed)

        if invalid_keys:
            raise serializers.ValidationError(
                f"These filters are not allowed on your plan: {', '.join(sorted(invalid_keys))}"
            )

        return value

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip()

            