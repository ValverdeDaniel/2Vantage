from django.urls import path

from . import file_views, roster_views, views

urlpatterns = [
    path('deals/<int:pk>/census/', views.CensusView.as_view()),
    path('deals/<int:pk>/census/imports/', views.ImportsView.as_view()),
    path('census/imports/<int:import_id>/', views.ImportView.as_view()),
    path('census/imports/<int:import_id>/apply/', views.ApplyView.as_view()),
    path('census/imports/<int:import_id>/discard/', views.DiscardView.as_view()),
    path('deals/<int:pk>/census/members/', roster_views.MembersView.as_view()),
    path('census/members/<int:member_id>/', roster_views.MemberView.as_view()),
    path('census/members/<int:member_id>/source/', roster_views.MemberSourceView.as_view()),
    path('deals/<int:pk>/census/clear/', roster_views.ClearView.as_view()),
    path('deals/<int:pk>/census/marks/', roster_views.MarksView.as_view()),
    path('deals/<int:pk>/census/missing/', roster_views.MissingView.as_view()),
    path('deals/<int:pk>/census/template/', file_views.TemplateView.as_view()),
    path('deals/<int:pk>/census/export/', file_views.ExportView.as_view()),
]
