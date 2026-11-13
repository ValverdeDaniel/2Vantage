from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/overview/', views.DealOverviewView.as_view()),
    path('deals/<int:pk>/overview/feed/', views.DealFeedView.as_view()),
    path('clients/<int:pk>/overview/', views.ClientOverviewView.as_view()),
    path('clients/<int:pk>/activity/', views.ClientFeedView.as_view()),
]
