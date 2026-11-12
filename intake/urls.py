from django.urls import path

from . import views

urlpatterns = [
    path('deals/<int:pk>/intake/', views.IntakeView.as_view()),
    path('deals/<int:pk>/intake/marks/', views.MarksView.as_view()),
    path('deals/<int:pk>/intake/source/', views.SourceView.as_view()),
    path('deals/<int:pk>/intake/checklist/', views.ChecklistView.as_view()),
    path('deals/<int:pk>/intake/intent/', views.IntentView.as_view()),
    path('deals/<int:pk>/intake/intent/confirm/', views.ConfirmIntentView.as_view()),
    path('deals/<int:pk>/intake/intent/reopen/', views.ReopenIntentView.as_view()),
    path('deals/<int:pk>/coverage/', views.CoverageListView.as_view()),
    path('coverage/<int:coverage_id>/', views.CoverageView.as_view()),
]
