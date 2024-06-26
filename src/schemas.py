from .extensions import ma
from marshmallow import fields
from .models import Comment, Post
import re
import json
from datetime import datetime
from src.util import handle_pagination


class CommentSchema(ma.SQLAlchemyAutoSchema):
    message = ma.Method("deserialize_message", dump_only=True)

    def de_me(self, message):
        deserialized = []
        for item in message:
            try:
                item_dict = json.loads(item)
                for key in item_dict:
                    if key == "message":
                        try:
                            item_dict[key] = self.de_me(item_dict[key])
                        except Exception as e:
                            print("ERROR ERROR ERROR")
                            print(e)

                deserialized.append(item_dict)

            except json.JSONDecodeError:
                deserialized.append(item)
        return deserialized

    def deserialize_message(self, comment):
        deserialized = []
        deserialized = self.de_me(comment.message)
        return deserialized

    def convert_dict(self, quote_dict):
        deserialized = {}
        for key, value in quote_dict.items():
            if key == "created_at" and value:
                try:
                    format_date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
                    formatted_date = format_date.strftime("%a, %d %B %Y, %H:%M:%S")
                    print(formatted_date)
                    deserialized[key] = formatted_date
                except ValueError:
                    deserialized[key] = value
                    pass
            elif isinstance(value, dict):
                deserialized[key] = self.convert_dict(
                    value
                )  # Recursively handle nested dictionaries
            else:
                deserialized[key] = value
        return deserialized

    class Meta:
        model = Comment
        include_fk = True


class ImageSchema(ma.SQLAlchemyAutoSchema):
    def get_image_urls(self, images):
        adjusted_for_missing_order = [
            {"image_url": image.image_url, "order": image.order or idx, "id": image.id}
            for idx, image in enumerate(images)
        ]

        return [image["image_url"] for image in adjusted_for_missing_order]

    class Meta:
        fields = ("id", "image_url", "order")


class PostSchema(ma.SQLAlchemyAutoSchema):
    images = ma.Method("get_image_urls", dump_only=True)
    comments = fields.Method("comment_pagination", dump_only=True)
    title = ma.Method("transform_title", dump_only=True)

    def comment_pagination(self, post):
        if not post.comments:
            return {}
        comment_schema = CommentSchema(many=True)
        items = comment_schema.dump(post.comments)
        return {
            "page_info": handle_pagination(post.comment_pagination),
            "items": items,
        }

    def get_image_urls(self, post):
        schema = ImageSchema()
        return schema.get_image_urls(post.images)

    def transform_title(self, post):
        patterns_to_remove = ["\[IC\]", "【IC】", "\[GB\]", "【GB】"]

        # Combine patterns into a single regular expression
        combined_pattern = "|".join(patterns_to_remove)

        # Use regular expression substitution for pattern removal
        title_without_patterns = re.sub(combined_pattern, "", post.title)

        # Replace consecutive spaces with a single space
        title_without_patterns = re.sub(r"\s+", " ", title_without_patterns)

        return title_without_patterns.strip()

    class Meta:
        model = Post
        include_fk = True


posts_schema = PostSchema(many=True)
post_schema = PostSchema()

images_schema = ImageSchema(many=True)
image_schema = ImageSchema()

comments_schema = CommentSchema(many=True)
comment_schema = CommentSchema()
