from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/agenda/', views.DealAgendaView.as_view()),
    path('deals/<int:pk>/journey/', views.DealJourneyView.as_view()),
    path('work-queue/', views.WorkQueueView.as_view()),
    path('work-queue/stats/', views.WorkQueueStatsView.as_view()),
    path('deals/<int:pk>/agenda/marks/', views.MarksView.as_view()),
    path('deals/<int:pk>/agenda/marks/<str:step_key>/', views.MarkView.as_view()),
    path('deals/<int:pk>/agenda/follow-ups/', views.FollowUpsView.as_view()),
    path('deals/<int:pk>/tasks/', views.DealTasksView.as_view()),
    path('tasks/<int:pk>/', views.TaskView.as_view()),
]
