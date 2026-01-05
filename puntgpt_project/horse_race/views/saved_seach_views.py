from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.utils.response import success_response, error_response
from subscription.models import UserSubscription
from horse_race.models.saved_search_model import SavedSearch
from horse_race.serializers.saved_search_serializers import SavedSearchSerializer



class SavedSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request):
        try:
            user = request.user
            saved_searches = SavedSearch.objects.filter(user=user).order_by('-updated_at')          
            serializer = SavedSearchSerializer(saved_searches,many=True)
            response, code = success_response(
                "Saved searches fetched successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
            return Response(response, status=code)
           
        except Exception as e:
            response, code = error_response(
                "Failed to fetch saved searches.",
                errors={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response(response, status=code)


    def post(self, request):

        try: 
            user = request.user
            subscription = UserSubscription.objects.filter(user=user).first()

            if not subscription:
                response, code = error_response(
                    "User does not have a subscription.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
                return Response(response, status=code)

            current_subscription = subscription.plan.plan
            saved_search_count = SavedSearch.objects.filter(user=user).count()

            if current_subscription == "Free ‘Mug Punter’ Account" and saved_search_count >= 3:
                response, code = error_response(
                    "Upgrade to Pro Punter to save more than 3 searches.",
                    status_code=status.HTTP_403_FORBIDDEN 
                )
                return Response(response, status=code)
            
            else:                
                serializer = SavedSearchSerializer(data=request.data, context={'request': request})

                if serializer.is_valid():
                    serializer.save(user=user)
                    response, code = success_response(
                            "Search saved successfully.",
                            data=serializer.data,
                            status_code=status.HTTP_201_CREATED
                        )
                else:                  
                   response, code = error_response(
                    "Invalid data.",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                   )

                return Response(response, status=code)
            
        except Exception as e:
            response, code = error_response(
                "Failed to save search.",
                errors={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response(response, status=code)
        


class SavedSearchDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            search = SavedSearch.objects.get(pk=pk,user=request.user)
            search.delete()
            response, code = success_response(
                "Search deleted successfully.",
                status_code=status.HTTP_204_NO_CONTENT
            )
            
            return Response(response, status=code)
        except SavedSearch.DoesNotExist:
            response, code = error_response(
                "Search not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
            return Response(response, status=code)
        

    def get(self, request, pk):
        try:
            search = SavedSearch.objects.get(pk=pk,user=request.user)
            serializer = SavedSearchSerializer(search)
            response, code = success_response(
                "Search fetched successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
            return Response(response, status=code)
        except SavedSearch.DoesNotExist:
            response, code = error_response(
                "Search not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
            return Response(response, status=code)
        

    def patch(self, request, pk):
        try:
            search = SavedSearch.objects.get(pk=pk,user=request.user)
            serializer = SavedSearchSerializer(search, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                response, code = success_response(
                    "Search updated successfully.",
                    data=serializer.data,
                    status_code=status.HTTP_200_OK
                )
                return Response(response, status=code)
            else:
                response, code = error_response(
                    "Invalid data.",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
                return Response(response, status=code)
            
        except SavedSearch.DoesNotExist:
            response, code = error_response(
                "Search not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
            return Response(response, status=code)


       

       