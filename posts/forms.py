from django.forms import ModelForm, Textarea

from posts.models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ['group', 'text', 'image']


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': Textarea()
        }
