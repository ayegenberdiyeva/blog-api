from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from django.db.models import QuerySet

from apps.blog.models import Category, Comment, Post, Tag
from apps.blog.permissions import IsAuthorOrStaffOrReadOnly, IsStaffOrReadOnly
from apps.blog.selectors import visible_posts
from apps.blog.serializers import (
    CategorySerializer,
    CommentSerializer,
    PostSerializer,
    TagSerializer,
)


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrReadOnly]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "id"]


class TagViewSet(ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsStaffOrReadOnly]
    search_fields = ["name", "slug"]
    ordering_fields = ["name", "id"]


class PostViewSet(ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrStaffOrReadOnly]
    search_fields = ["title", "body"]
    ordering_fields = ["created_at", "updated_at", "title", "id"]

    def get_queryset(self) -> QuerySet[Post]:
        return visible_posts(self.request.user)

    def perform_create(self, serializer: PostSerializer) -> None:
        serializer.save(author=self.request.user)


class CommentViewSet(ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrStaffOrReadOnly]
    search_fields = ["body"]
    ordering_fields = ["created_at", "id"]

    def get_queryset(self) -> QuerySet[Comment]:
        return Comment.objects.filter(
            post__in=visible_posts(self.request.user)
        ).select_related("post", "author")

    def perform_create(self, serializer: CommentSerializer) -> None:
        serializer.save(author=self.request.user)
