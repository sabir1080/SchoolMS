from django.urls import path
from rest_framework.routers import DefaultRouter

from .promotion import PromotionView
from .views import GuardianViewSet, MyChildrenView, MyStudentProfileView, StudentViewSet

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("guardians", GuardianViewSet, basename="guardian")

urlpatterns = [
    path("students/promotion/", PromotionView.as_view(), name="student-promotion"),
    path("me/children/", MyChildrenView.as_view(), name="my-children"),
    path("me/student/", MyStudentProfileView.as_view(), name="my-student"),
    *router.urls,
]
