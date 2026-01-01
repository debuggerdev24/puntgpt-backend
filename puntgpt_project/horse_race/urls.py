from django.urls import path
from horse_race.views.upcoming_runners_views import *
from horse_race.views.track_displaying_views import *
from horse_race.views.distance_displaying_views import *

urlpatterns =[
    # functionality views: 
    path('upcoming-runners/', UpcomingRunnersView.as_view(), name='upcoming-runners'),


    # display views:
    path('track-displaying/', TrackDisplayingView.as_view(), name='track-displaying'),
    path('distance-displaying/', DistanceDisplayingView.as_view(), name='distance-displaying'),
]