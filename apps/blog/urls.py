from rest_framework.routers import DefaultRouter

from apps.blog.views import CategoryViewSet, CommentViewSet, PostViewSet, TagViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("tags", TagViewSet, basename="tag")
router.register("posts", PostViewSet, basename="post")
router.register("comments", CommentViewSet, basename="comment")
urlpatterns = router.urls
