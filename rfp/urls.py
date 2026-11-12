from django.urls import path

from . import check_views, file_views, lens_views, views

urlpatterns = [
    path('deals/<int:pk>/rfp/', views.RfpView.as_view()),
    path('deals/<int:pk>/rfp/done/', views.DoneView.as_view()),
    path('deals/<int:pk>/rfp/checks/', check_views.ChecksView.as_view()),
    path('deals/<int:pk>/rfp/check/', check_views.CheckView.as_view()),
    path('deals/<int:pk>/rfp/drafts/<str:key>/sent/', views.SentView.as_view()),
    path('deals/<int:pk>/rfp/files/<str:key>/', file_views.FileView.as_view()),
    path('deals/<int:pk>/rfp/files/<str:key>/look/', file_views.LookView.as_view()),
    path('deals/<int:pk>/rfp/formats/', lens_views.FormatsView.as_view()),
    path('deals/<int:pk>/rfp/formats/<str:key>/', lens_views.FormatView.as_view()),
]
