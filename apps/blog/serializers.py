from typing import Any

from rest_framework import serializers

from django.contrib.auth.models import AnonymousUser

from apps.blog.models import Category, Comment, Post, Tag
from apps.blog.selectors import visible_posts


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "slug",
            "body",
            "category",
            "tags",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "post", "author", "body", "created_at")
        read_only_fields = ("id", "author", "created_at")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = request.user if request else AnonymousUser()
        self.fields["post"].queryset = visible_posts(user)

    def validate_post(self, value: Post) -> Post:
        if self.instance and value.pk != self.instance.post_id:
            raise serializers.ValidationError(
                "A comment cannot be moved to another post."
            )
        return value
