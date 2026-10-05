"""One visibility rule shared by posts and comments."""

from django.contrib.auth.models import AnonymousUser
from django.db.models import Q, QuerySet

from apps.auths.models import User
from apps.blog.models import Post


def visible_posts(user: User | AnonymousUser) -> QuerySet[Post]:
    queryset = Post.objects.select_related("author", "category").prefetch_related(
        "tags"
    )
    if user.is_authenticated and user.is_staff:
        return queryset
    public = Q(status=Post.Status.PUBLISHED)
    if user.is_authenticated:
        return queryset.filter(public | Q(author=user))
    return queryset.filter(public)
