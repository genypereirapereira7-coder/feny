from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.projects.api.views import ProjectViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")

urlpatterns = [path("", include(router.urls))]
