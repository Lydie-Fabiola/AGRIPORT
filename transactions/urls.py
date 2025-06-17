from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, MoMoWebhookView

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = router.urls + [
    path('momo/webhook/', MoMoWebhookView.as_view(), name='momo-webhook'),
] 