from django.urls import path

from . import people_views, views

urlpatterns = [
    path('deals/<int:pk>/commission/', views.DealCommissionView.as_view()),
    path('deals/<int:pk>/commission/split/', views.DealSplitView.as_view()),
    path('deals/<int:pk>/commission/split/preview/', views.DealSplitPreviewView.as_view()),
    path('clients/<int:pk>/commission/split/', views.ClientSplitView.as_view()),
    path('clients/<int:pk>/commission/split/preview/', views.ClientSplitPreviewView.as_view()),
    path('commissions/parties/', people_views.PartiesView.as_view()),
    path('commissions/parties/<int:pk>/', people_views.PartyView.as_view()),
    path('commissions/settings/', people_views.SettingsView.as_view()),
]
