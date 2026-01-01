from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.utils.response import success_response, error_response
from horse_race.models.horse import HorseStatistic


class DistanceDisplayingView(APIView):
    def get(self,request,format=None):

        distance_range = list(HorseStatistic.objects.filter(category ='distance')
                              .values_list('value', flat=True).distinct().order_by('value'))
        
        # removing the unnecessary single quotes in the resultant values
        distance_range = [item.replace("'", "") if isinstance(item, str) else item for item in distance_range]
    
        if not distance_range:
            response, code = error_response(
                "Distance displaying failed",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        else:
            response, code = success_response(
                "Distance displaying successfully",
                data=distance_range,
                status_code=status.HTTP_200_OK
            )
        
        return Response(response, status=code)
        