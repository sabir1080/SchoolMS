from django.urls import path

from .views import (
    AcceptTrialView,
    InstituteAgreementDetailView,
    InstituteAgreementPreviewView,
    InstituteAgreementsView,
    PlatformAgreementDetailView,
    PlatformAgreementsView,
    ProviderProfileView,
    PublicTrialAgreementView,
)

urlpatterns = [
    path("public/agreements/trial/", PublicTrialAgreementView.as_view(), name="public-trial-agreement"),
    path("agreements/", InstituteAgreementsView.as_view(), name="agreements"),
    path("agreements/preview/", InstituteAgreementPreviewView.as_view(), name="agreement-preview"),
    path("agreements/accept-trial/", AcceptTrialView.as_view(), name="agreement-accept-trial"),
    path("agreements/<int:pk>/", InstituteAgreementDetailView.as_view(), name="agreement-detail"),
    path("platform/profile/", ProviderProfileView.as_view(), name="platform-profile"),
    path("platform/agreements/", PlatformAgreementsView.as_view(), name="platform-agreements"),
    path("platform/agreements/<int:pk>/", PlatformAgreementDetailView.as_view(), name="platform-agreement-detail"),
]
