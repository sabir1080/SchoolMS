from rest_framework.routers import DefaultRouter

from .views import AcademicSessionViewSet, ProgramViewSet, SectionViewSet, SubjectViewSet

router = DefaultRouter()
router.register("academics/sessions", AcademicSessionViewSet, basename="academic-session")
router.register("academics/programs", ProgramViewSet, basename="program")
router.register("academics/sections", SectionViewSet, basename="section")
router.register("academics/subjects", SubjectViewSet, basename="subject")

urlpatterns = router.urls
