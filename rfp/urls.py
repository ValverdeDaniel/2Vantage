from django.urls import path

from . import file_views, lens_views, views

urlpatterns = [
    path('deals/<int:pk>/rfp/', views.RfpView.as_view()),
    path('deals/<int:pk>/rfp/done/', views.DoneView.as_view()),
    path('deals/<int:pk>/rfp/files/<str:key>/', file_views.FileView.as_view()),
    path('deals/<int:pk>/rfp/files/<str:key>/look/', file_views.LookView.as_view()),
    path('deals/<int:pk>/rfp/formats/', lens_views.FormatsView.as_view()),
    path('deals/<int:pk>/rfp/formats/<str:key>/', lens_views.FormatView.as_view()),
]
