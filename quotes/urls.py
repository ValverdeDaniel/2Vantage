from django.urls import path

from . import template_views, views

urlpatterns = [
    path('deals/<int:pk>/plans/lines/', views.LinesView.as_view()),
    path('deals/<int:pk>/plans/', views.PlansView.as_view()),
    path('deals/<int:pk>/plans/star/', views.StarView.as_view()),
    path('deals/<int:pk>/plans/enrollment/', views.EnrollmentView.as_view()),
    path('deals/<int:pk>/plans/order/', views.OrderView.as_view()),
    path('deals/<int:pk>/plans/packages/', views.PackagesView.as_view()),
    path('deals/<int:pk>/plans/template/', template_views.TemplateDownloadView.as_view()),
    path('deals/<int:pk>/plans/import/', template_views.TemplateImportView.as_view()),
    path('plans/<int:plan_id>/', views.PlanView.as_view()),
    path('plans/<int:plan_id>/renewal/', views.RenewalView.as_view()),
    path('plans/<int:plan_id>/copy/', views.CopyView.as_view()),
    path('plans/<int:plan_id>/sold/', views.SoldView.as_view()),
    path('plans/<int:plan_id>/recommend/', views.RecommendView.as_view()),
    path('packages/<int:package_id>/', views.PackageView.as_view()),
]
