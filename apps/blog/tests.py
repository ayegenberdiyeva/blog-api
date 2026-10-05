from typing import Any

from rest_framework import status
from rest_framework.test import APITestCase

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

TEST_PASSWORD = "Lake!Forest91-Glacier"


def make_user(email: str, **extra: Any) -> User:
    return User.objects.create_user(
        email=email,
        password=TEST_PASSWORD,
        first_name="Test",
        last_name="Author",
        **extra,
    )


class BlogModelTests(TestCase):
    def setUp(self) -> None:
        self.author = make_user("author@example.com")
        self.category = Category.objects.create(name="Django", slug="django")
        self.post = Post.objects.create(
            author=self.author,
            title="First post",
            slug="first-post",
            body="Hello",
            category=self.category,
        )

    def test_optional_category_tags_defaults_and_timestamps(self) -> None:
        post = Post.objects.create(
            author=self.author, title="Optional", slug="optional", body="Body"
        )
        post.full_clean()
        self.assertIsNone(post.category)
        self.assertFalse(post.tags.exists())
        self.assertEqual(post.status, Post.Status.DRAFT)
        first = Tag.objects.create(name="Python", slug="python")
        second = Tag.objects.create(name="Web", slug="web")
        post.tags.add(first, second)
        self.assertEqual(post.tags.count(), 2)
        created, updated = post.created_at, post.updated_at
        post.body = "Updated"
        post.save()
        post.refresh_from_db()
        self.assertEqual(post.created_at, created)
        self.assertGreater(post.updated_at, updated)

    def test_category_deletion_sets_null_and_tag_deletion_keeps_post(self) -> None:
        tag = Tag.objects.create(name="Tag", slug="tag")
        self.post.tags.add(tag)
        self.category.delete()
        tag.delete()
        self.post.refresh_from_db()
        self.assertIsNone(self.post.category)
        self.assertFalse(self.post.tags.exists())

    def test_post_deletion_cascades_to_comments(self) -> None:
        comment = Comment.objects.create(
            post=self.post, author=self.author, body="Reply"
        )
        self.post.delete()
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.author.pk).exists())

    def test_user_deletion_cascades_to_posts_and_comments(self) -> None:
        other = make_user("other@example.com")
        other_post = Post.objects.create(
            author=other, title="Other", slug="other", body="B"
        )
        Comment.objects.create(post=other_post, author=self.author, body="Reply")
        Comment.objects.create(post=self.post, author=other, body="Reply")
        self.author.delete()
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())
        self.assertFalse(Comment.objects.exists())
        self.assertTrue(Post.objects.filter(pk=other_post.pk).exists())

    def test_unique_fields_and_status_constraint(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="Django", slug="different")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="Different", slug="django")
        tag = Tag.objects.create(name="Python", slug="python")
        for values in (
            {"name": tag.name, "slug": "other"},
            {"name": "Other", "slug": tag.slug},
        ):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Tag.objects.create(**values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Post.objects.create(
                author=self.author, title="Duplicate", slug=self.post.slug, body="Body"
            )
        self.post.status = "unknown"
        with self.assertRaises(ValidationError):
            self.post.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.post.save()


class BlogAPITests(APITestCase):
    def setUp(self) -> None:
        self.author = make_user("author@example.com")
        self.other = make_user("other@example.com")
        self.staff = make_user("staff@example.com", is_staff=True)
        self.public = Post.objects.create(
            author=self.author,
            title="Public",
            slug="public",
            body="Published body",
            status=Post.Status.PUBLISHED,
        )
        self.draft = Post.objects.create(
            author=self.author,
            title="Draft",
            slug="draft",
            body="Private body",
        )
        self.comment = Comment.objects.create(
            author=self.author, post=self.public, body="Public reply"
        )
        self.private_comment = Comment.objects.create(
            author=self.author, post=self.draft, body="Private reply"
        )

    def test_anonymous_reads_only_published_posts_and_comments(self) -> None:
        for endpoint, visible, hidden in (
            ("post", self.public, self.draft),
            ("comment", self.comment, self.private_comment),
        ):
            response = self.client.get(reverse(f"{endpoint}-list"))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual([r["id"] for r in response.data["results"]], [visible.pk])
            response = self.client.get(reverse(f"{endpoint}-detail", args=[hidden.pk]))
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_author_and_staff_can_view_drafts_other_user_cannot(self) -> None:
        for user, expected in (
            (self.author, status.HTTP_200_OK),
            (self.staff, status.HTTP_200_OK),
            (self.other, status.HTTP_404_NOT_FOUND),
        ):
            self.client.force_authenticate(user)
            for endpoint, obj in (
                ("post", self.draft),
                ("comment", self.private_comment),
            ):
                response = self.client.get(reverse(f"{endpoint}-detail", args=[obj.pk]))
                self.assertEqual(response.status_code, expected)

    def test_anonymous_cannot_write(self) -> None:
        response = self.client.post(
            reverse("post-list"),
            {
                "title": "New",
                "slug": "new",
                "body": "Body",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post(
            reverse("comment-list"),
            {
                "post": self.public.pk,
                "body": "Reply",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_create_update_delete_and_author_cannot_be_spoofed(self) -> None:
        self.client.force_authenticate(self.other)
        response = self.client.post(
            reverse("post-list"),
            {
                "title": "New",
                "slug": "new",
                "body": "Body",
                "author": self.author.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"], self.other.pk)
        url = reverse("post-detail", args=[response.data["id"]])
        response = self.client.patch(url, {"status": Post.Status.PUBLISHED})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Post.Status.PUBLISHED)
        self.assertEqual(
            self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT
        )

    def test_other_user_cannot_modify_or_delete_public_content(self) -> None:
        self.client.force_authenticate(self.other)
        for endpoint, obj in (("post", self.public), ("comment", self.comment)):
            url = reverse(f"{endpoint}-detail", args=[obj.pk])
            self.assertEqual(
                self.client.patch(url, {"body": "Hijacked"}).status_code,
                status.HTTP_403_FORBIDDEN,
            )
            self.assertEqual(
                self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN
            )

    def test_staff_can_moderate_other_users_content(self) -> None:
        self.client.force_authenticate(self.staff)
        url = reverse("post-detail", args=[self.public.pk])
        self.assertEqual(
            self.client.patch(url, {"body": "Moderated"}).status_code,
            status.HTTP_200_OK,
        )
        url = reverse("comment-detail", args=[self.comment.pk])
        self.assertEqual(
            self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT
        )

    def test_comment_creation_respects_post_visibility_and_ownership(self) -> None:
        self.client.force_authenticate(self.other)
        response = self.client.post(
            reverse("comment-list"),
            {
                "post": self.draft.pk,
                "body": "Intrusion",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(
            reverse("comment-list"),
            {
                "post": self.public.pk,
                "body": "Reply",
                "author": self.author.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"], self.other.pk)
        url = reverse("comment-detail", args=[response.data["id"]])
        self.assertEqual(
            self.client.patch(url, {"body": "Edited"}).status_code, status.HTTP_200_OK
        )
        self.assertEqual(
            self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT
        )

    def test_comment_cannot_move_to_another_post(self) -> None:
        self.client.force_authenticate(self.author)
        response = self.client.patch(
            reverse("comment-detail", args=[self.comment.pk]),
            {
                "post": self.draft.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_taxonomy_public_read_staff_write(self) -> None:
        for endpoint in ("category", "tag"):
            url = reverse(f"{endpoint}-list")
            self.client.force_authenticate(None)
            self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
            self.client.force_authenticate(self.other)
            response = self.client.post(url, {"name": "Python", "slug": "python"})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.client.force_authenticate(self.staff)
            response = self.client.post(url, {"name": "Python", "slug": "python"})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            detail = reverse(f"{endpoint}-detail", args=[response.data["id"]])
            self.assertEqual(
                self.client.patch(detail, {"name": "Web"}).status_code,
                status.HTTP_200_OK,
            )
            self.assertEqual(
                self.client.delete(detail).status_code, status.HTTP_204_NO_CONTENT
            )

    def test_api_validates_unique_slug_status_and_relations(self) -> None:
        self.client.force_authenticate(self.author)
        base = {"title": "New", "slug": "new", "body": "Body"}
        for overrides in (
            {"slug": self.public.slug},
            {"status": "bad"},
            {"category": 999999},
            {"tags": [999999]},
        ):
            response = self.client.post(
                reverse("post-list"), {**base, **overrides}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_and_pagination_preserve_draft_privacy(self) -> None:
        response = self.client.get(reverse("post-list"), {"search": "Private"})
        self.assertEqual(response.data["count"], 0)
        self.assertIn("results", response.data)
