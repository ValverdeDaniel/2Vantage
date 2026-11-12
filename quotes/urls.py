from django.urls import path

from . import (
    arrange_views,
    board_views,
    layout_views,
    mark_views,
    move_views,
    priced_views,
    review_views,
    sbc_views,
    source_views,
    template_views,
    views,
)

urlpatterns = [
    path('deals/<int:pk>/plans/lines/', views.LinesView.as_view()),
    path('deals/<int:pk>/plans/', views.PlansView.as_view()),
    path('deals/<int:pk>/plans/star/', mark_views.StarView.as_view()),
    path('deals/<int:pk>/plans/shortlist/clear/', mark_views.ClearShortlistView.as_view()),
    path('deals/<int:pk>/plans/role/', arrange_views.RoleView.as_view()),
    path('deals/<int:pk>/plans/links/', arrange_views.LinksView.as_view()),
    path('deals/<int:pk>/plans/order/', arrange_views.OrderView.as_view()),
    path('deals/<int:pk>/plans/slot/', arrange_views.SlotView.as_view()),
    path('deals/<int:pk>/plans/move-line/', move_views.MoveLineView.as_view()),
    path('deals/<int:pk>/plans/delete/', move_views.DeleteView.as_view()),
    path('deals/<int:pk>/plans/clear/', move_views.ClearView.as_view()),
    path('deals/<int:pk>/plans/enrollment/', views.EnrollmentView.as_view()),
    path('deals/<int:pk>/plans/packages/', views.PackagesView.as_view()),
    path('deals/<int:pk>/plans/template/', template_views.TemplateDownloadView.as_view()),
    path('deals/<int:pk>/plans/import/', template_views.TemplateImportView.as_view()),
    path('deals/<int:pk>/plans/board-export/', views.BoardExportView.as_view()),  # ⤓ Export (F93; slice 9)
    path('deals/<int:pk>/plans/find/', board_views.FindView.as_view()),  # the finder's index (F14, F15; slice 10)
    path('deals/<int:pk>/plans/sources/', review_views.SourcesView.as_view()),  # the station's List (E56; slice 17)
    path('deals/<int:pk>/plans/marks/', review_views.MarksView.as_view()),  # approve, ignore, check, clear (E85)
    path('deals/<int:pk>/plans/priced/', priced_views.PricedView.as_view()),  # priced versions, dry run (F76; s35)
    path('deals/<int:pk>/plans/as-quoted/', layout_views.AsQuotedView.as_view()),  # printed tables (F42, E42; s21)
    path('plans/<int:plan_id>/', views.PlanView.as_view()),
    path('plans/<int:plan_id>/source/', source_views.PlanSourceView.as_view()),  # ↗ open in file (slice 15, E18)
    path('plans/<int:plan_id>/renewal/', views.RenewalView.as_view()),
    path('plans/<int:plan_id>/copy/', views.CopyView.as_view()),
    path('plans/<int:plan_id>/priced/', priced_views.RepriceView.as_view()),  # ✎ re-price a version (F82; slice 35)
    path('plans/<int:plan_id>/sbc/', sbc_views.AttachSbcView.as_view()),  # Attach SBC…: a staged read (D38; s22)
    path('plans/<int:plan_id>/sold/', mark_views.SoldView.as_view()),
    path('plans/<int:plan_id>/recommend/', mark_views.RecommendView.as_view()),
    path('packages/<int:package_id>/', views.PackageView.as_view()),
    path('saved-views/', board_views.SavedViewsView.as_view()),  # saved board setups (F28; slice 10)
    path('saved-views/<int:view_id>/', board_views.SavedViewView.as_view()),
]
