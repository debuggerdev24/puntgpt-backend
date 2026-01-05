from django.urls import path
from horse_race.views.upcoming_runners_views import *
from horse_race.views.track_displaying_views import *
from horse_race.views.distance_displaying_views import *
from horse_race.views.search_filter_display_views import *
from horse_race.views.saved_seach_views import *

urlpatterns =[
    # functionality views: 
    path('upcoming-runners/', UpcomingRunnersView.as_view(), name='upcoming-runners'),
    path('saved-search/', SavedSearchView.as_view(), name='saved-search'),
    path('saved-search/<int:pk>/', SavedSearchDetailView.as_view(), name='saved-search-detail'),


    # display views:
    path('track-displaying/', TrackDisplayingView.as_view(), name='track-displaying'),
    path('distance-displaying/', DistanceDisplayingView.as_view(), name='distance-displaying'),
    path('search-filter-display/', SearchFilterDisplayView.as_view(), name='search-filter-display'),

]