from django.shortcuts import render
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, AlertViewSet
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification, Alert
from .serializers import NotificationSerializer, AlertSerializer
from farmer.models import FarmerProfile
from django.utils import timezone

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'alerts', AlertViewSet, basename='alert')

urlpatterns = router.urls

# Create your views here.

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Alert.objects.filter(farmer__user=user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        alert = self.get_object()
        alert.is_read = True
        alert.save()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def create_weather_alert(self, request):
        """Admin endpoint to broadcast a weather alert to all farmers."""
        title = request.data.get('title', 'Weather Alert')
        message = request.data.get('message', '')
        severity = request.data.get('severity', 'info')
        valid_until = request.data.get('valid_until')
        farmers = FarmerProfile.objects.all()
        alerts = []
        for farmer in farmers:
            alert = Alert.objects.create(
                farmer=farmer,
                alert_type='weather',
                title=title,
                message=message,
                severity=severity,
                valid_until=valid_until
            )
            alerts.append(alert)
        return Response({'created': len(alerts)}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def create_pest_alert(self, request):
        """Admin endpoint to broadcast a pest/disease alert to all farmers."""
        title = request.data.get('title', 'Pest Alert')
        message = request.data.get('message', '')
        severity = request.data.get('severity', 'warning')
        valid_until = request.data.get('valid_until')
        farmers = FarmerProfile.objects.all()
        alerts = []
        for farmer in farmers:
            alert = Alert.objects.create(
                farmer=farmer,
                alert_type='pest',
                title=title,
                message=message,
                severity=severity,
                valid_until=valid_until
            )
            alerts.append(alert)
        return Response({'created': len(alerts)}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def broadcast_best_practice(self, request):
        """Admin endpoint to broadcast a best practice tip to all farmers as an alert."""
        title = request.data.get('title', 'Farming Best Practice')
        message = request.data.get('message', '')
        severity = request.data.get('severity', 'info')
        valid_until = request.data.get('valid_until')
        farmers = FarmerProfile.objects.all()
        alerts = []
        for farmer in farmers:
            alert = Alert.objects.create(
                farmer=farmer,
                alert_type='system',
                title=title,
                message=message,
                severity=severity,
                valid_until=valid_until
            )
            alerts.append(alert)
        return Response({'created': len(alerts)}, status=status.HTTP_201_CREATED)
