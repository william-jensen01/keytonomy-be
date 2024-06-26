from .extensions import db
import json
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime


class Post(db.Model):
    topic_id = db.Column(db.Integer, primary_key=True, nullable=False)
    title = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)
    creator = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False)
    post_type = db.Column(db.String(2), nullable=False)

    images = db.relationship(
        "Image",
        cascade="all,delete",
        backref="post",
        order_by="asc(Image.order)",
        lazy="noload",
    )

    comments = db.relationship(
        "Comment",
        cascade="all,delete",
        backref="post",
        order_by="asc(Comment.number)",
        lazy="noload",
    )

    def __init__(self, title, topic_id, url, creator, created, last_updated, post_type):
        self.topic_id = topic_id
        self.title = title
        self.url = url
        self.creator = creator
        self.created = created
        self.last_updated = last_updated
        self.post_type = post_type

    def handle_include_comments(
        posts, include_comments, comment_page, comment_per_page
    ):
        if comment_page is not None and comment_per_page is not None:
            if include_comments:
                if isinstance(posts, list):
                    for post in posts:
                        comment_pagination = (
                            Comment.query.filter_by(post_topic_id=post.topic_id)
                            .order_by(Comment.number.desc())
                            .paginate(page=comment_page, per_page=comment_per_page)
                        )
                        post.comments = comment_pagination.items
                        post.comment_pagination = comment_pagination
                elif isinstance(posts, dict):
                    comment_pagination = (
                        Comment.query.filter_by(post_topic_id=posts.topic_id)
                        .order_by(Comment.number.desc())
                        .paginate(page=comment_page, per_page=comment_per_page)
                    )
                    post.comments = comment_pagination.items
                    post.comment_pagination = comment_pagination
        return posts

    def get(
        many=False,
        page=None,
        per_page=None,
        include_images=True,
        include_comments=False,
        comment_page=1,
        comment_per_page=25,
        order_by=None,
        order_dir=None,
        **query_options,
    ):
        query = Post.query
        if include_images:
            query = query.options(db.joinedload(Post.images))
        for key, value in query_options.items():
            if hasattr(Post, key):
                column = getattr(Post, key)
                if isinstance(value, str):
                    query = query.filter(column.ilike(f"%{value}%"))
                else:
                    query = query.filter(column == value)
        if many:
            if order_by is not None and order_dir is not None:
                column = getattr(Post, order_by)
            if order_dir == "asc":
                query = query.order_by(column.asc())
            elif order_dir == "desc":
                query = query.order_by(column.desc())

            # Pagination (if page and per_page are specified)
            if isinstance(page, int) and isinstance(per_page, int):
                pagination = query.paginate(page=page, per_page=per_page)
                posts = pagination.items
                Post.handle_include_comments(
                    posts, include_comments, comment_page, comment_per_page
                )
                return posts, pagination

            # No pagination
            posts = query.all()
        else:
            posts = query.first()

        Post.handle_include_comments(
            posts, include_comments, comment_page, comment_per_page
        )

        return posts


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.Text)
    post_topic_id = db.Column(db.Integer, db.ForeignKey("post.topic_id"))
    order = db.Column(db.SmallInteger)

    def __init__(self, image_url, order, post):
        self.image_url = image_url
        self.order = order
        self.post_topic_id = post.topic_id


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer)
    post_topic_id = db.Column(db.Integer, db.ForeignKey("post.topic_id"))
    number = db.Column(db.SmallInteger)
    link = db.Column(db.String(80))  # currently at 67
    commenter = db.Column(db.Text)
    message = db.Column(ARRAY(db.Text))
    is_starter = db.Column(db.Boolean, default=False)
    attachment = db.Column(db.Text)
    created_at = db.Column(db.DateTime)

    def __init__(
        self,
        comment_id,
        post_topic_id,
        number,
        link,
        commenter,
        message,
        is_starter,
        attachment,
        created_at,
    ):
        self.message_id = comment_id
        self.post_topic_id = post_topic_id
        self.number = number
        self.link = link
        self.commenter = commenter
        self.message = message
        self.is_starter = is_starter
        self.attachment = attachment
        self.created_at = created_at
        self.message = self.serialize_message(message)

    def serialize_dict(self, d):
        serialized = {}
        for key, value in d.items():
            # if key == "created_at":
            #     serialized[key] = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            if isinstance(value, list):
                serialized[key] = self.serialize_message(value)
            else:
                serialized[key] = value
        return json.dumps(serialized)

    def serialize_message(self, message):
        serialized_list = []
        for item in message:
            if isinstance(item, dict):
                d = self.serialize_dict(item)
                serialized_list.append(d)
            elif isinstance(item, str):
                serialized_list.append(item)

        return serialized_list
