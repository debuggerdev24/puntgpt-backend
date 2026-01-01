from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from horse_race.models.track import Track
from accounts.utils.response import success_response, error_response


class TrackDisplayingView(APIView):
    def get(self, request, format=None):

        track = list(Track.objects.all().values_list('name', flat=True).distinct().order_by('name'))

        if track:
            response, code = success_response(
                "Track displaying successfully",
                data=track,
                status_code=status.HTTP_200_OK
            )

        else:
            response, code = error_response(
                "Track displaying failed",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        return Response(response, status=code)