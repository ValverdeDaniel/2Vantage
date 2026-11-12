from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/census/', views.CensusView.as_view()),
    path('deals/<int:pk>/census/imports/', views.ImportsView.as_view()),
    path('census/imports/<int:import_id>/', views.ImportView.as_view()),
    path('census/imports/<int:import_id>/apply/', views.ApplyView.as_view()),
    path('census/imports/<int:import_id>/discard/', views.DiscardView.as_view()),
]
