from rest_framework.routers import DefaultRouter
from .views import ReservationViewSet, ReviewViewSet

router = DefaultRouter()
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = router.urls 