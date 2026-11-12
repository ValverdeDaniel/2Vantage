from django.urls import path

from . import contacts_views, notes_views, views

urlpatterns = [
    path('clients/', views.ClientListView.as_view()),
    path('clients/<int:pk>/', views.ClientDetailView.as_view()),
    path('clients/<int:pk>/status/', views.ClientStatusView.as_view()),
    path('clients/<int:pk>/archive/', views.ClientArchiveView.as_view()),
    path('clients/<int:pk>/contacts/', contacts_views.ClientContactsView.as_view()),
    path('contacts/<int:pk>/', contacts_views.ContactView.as_view()),
    path('archived/', views.ArchivedView.as_view()),
    path('deals/<int:pk>/', views.DealView.as_view()),
    path('deals/<int:pk>/lost/', views.DealLostView.as_view()),
    path('deals/<int:pk>/reopen/', views.DealReopenView.as_view()),
    path('deals/<int:pk>/notes/', notes_views.DealNotesView.as_view()),
    path('notes/<int:pk>/', notes_views.NoteView.as_view()),
    path('deals/<int:pk>/activity/', views.DealActivityView.as_view()),
    path('activity/<int:pk>/revert/', views.ActivityRevertView.as_view()),
    path('users/', views.UserListView.as_view()),
    path('agency/', views.AgencyView.as_view()),
    path('agency/logo/', views.AgencyLogoView.as_view()),
]
