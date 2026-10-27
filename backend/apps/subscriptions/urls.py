from django.urls import path

from .views import MySubscriptionView, PublicPlanListView

urlpatterns = [
    path("public/plans/", PublicPlanListView.as_view(), name="public-plans"),
    path("subscription/", MySubscriptionView.as_view(), name="my-subscription"),
]
