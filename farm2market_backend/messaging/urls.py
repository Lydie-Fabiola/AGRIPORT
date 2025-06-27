"""
URL configuration for messaging app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'messaging'

router = DefaultRouter()
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'templates', views.MessageTemplateViewSet, basename='template')

urlpatterns = [
    path('', include(router.urls)),

    # Message Management
    path('mark-read/', views.MarkAsReadView.as_view(), name='mark-read'),
    path('unread-count/', views.UnreadCountView.as_view(), name='unread-count'),
    path('online-status/', views.OnlineStatusView.as_view(), name='online-status'),
]
