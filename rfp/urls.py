from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/rfp/', views.RfpView.as_view()),
    path('deals/<int:pk>/rfp/done/', views.DoneView.as_view()),
]
