from django.urls import path

from . import people_views, record_views, views

urlpatterns = [
    path('deals/<int:pk>/commission/', views.DealCommissionView.as_view()),
    path('deals/<int:pk>/commission/split/', views.DealSplitView.as_view()),
    path('deals/<int:pk>/commission/split/preview/', views.DealSplitPreviewView.as_view()),
    path('deals/<int:pk>/commission/book/', views.DealBookView.as_view()),
    path('deals/<int:pk>/commission/disclosure.pdf', views.DealDisclosureView.as_view()),
    path('clients/<int:pk>/commission/split/', views.ClientSplitView.as_view()),
    path('clients/<int:pk>/commission/split/preview/', views.ClientSplitPreviewView.as_view()),
    path('clients/<int:pk>/commission/records/', record_views.ClientRecordsView.as_view()),
    path('commissions/parties/', people_views.PartiesView.as_view()),
    path('commissions/parties/<int:pk>/', people_views.PartyView.as_view()),
    path('commissions/settings/', people_views.SettingsView.as_view()),
    path('commissions/records/', record_views.RecordsView.as_view()),
    path('commissions/records/export/', record_views.RecordsExportView.as_view()),
    path('commissions/records/<int:pk>/', record_views.RecordView.as_view()),
    path('commissions/records/<int:pk>/shares/', record_views.RecordSharesView.as_view()),
    path('commissions/records/<int:pk>/rebook/', record_views.RecordRebookView.as_view()),
    path('commissions/people/', record_views.PeopleView.as_view()),
    path('commissions/people/export/', record_views.PeopleExportView.as_view()),
    path('commissions/people/<str:key>/', record_views.PersonView.as_view()),
    path('commissions/clients/', record_views.ClientPickView.as_view()),
]
