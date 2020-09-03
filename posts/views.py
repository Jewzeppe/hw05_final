from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


@cache_page(20, key_prefix='index_page')
def index(request):
    """Функция отрисовки главной страницы."""
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'posts/index.html',
        {'page': page, 'paginator': paginator}
    )


def group_posts(request, slug):
    """Функция отрисовки постов группы."""
    group = get_object_or_404(Group, slug=slug)
    slug_posts = group.posts.all()
    paginator = Paginator(slug_posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'group.html',
        {'page': page, 'paginator': paginator, 'group': group}
    )


@login_required
def new_post(request):
    """Функция создания нового поста. Требует авторизации."""
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        form.instance.author = request.user
        form.save()
        return redirect('index')
    return render(
        request,
        'posts/new.html',
        {'form': form}
    )


def profile(request, username):
    """Функция отрисовки профиля автора."""
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    try:
        following = Follow.objects.filter(
            user__username=request.user,
            author__username=author
        ).exists()
    except TypeError:
        following = True
    context = {
            'page': page,
            'paginator': paginator,
            'author': author,
            'following': following
    }
    return render(
        request,
        'posts/profile.html',
        context
    )


def post_view(request, username, post_id):
    """Функция отображения поста."""
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    items = post.comments.all()
    return render(
        request,
        'posts/post_page.html',
        {
            'author': post.author,
            'post': post,
            'items': items,
            'form': CommentForm()
            }
    )


@login_required
def post_edit(request, username, post_id):
    """Функция редактирования поста.

    Относится к одному и тому же шаблону, что и функция создания нового
    поста. Внутри шаблона текст меняется в зависимости типа запроса.
    """
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    if request.user != post.author:
        return redirect('post', username=username, post_id=post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
        )
    if form.is_valid():
        form.save()
        return redirect('post', username=username, post_id=post_id)
    return render(
        request,
        'posts/new.html',
        {
            'form': form,
            'post': post
        }
    )


def page_not_found(request, exception):
    """Кастомная функция вывода страницы 404."""
    return render(
        request,
        'misc/404.html',
        {'path': request.path},
        status=404
    )


def server_error(request):
    """Кастомная функция вывода страницы 500."""
    return render(request, 'misc/500.html', status=500)


@login_required
def add_comment(request, username, post_id):
    """Функция добавления комментария."""
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    form = CommentForm(request.POST or None)
    items = post.comments.all()
    if not form.is_valid():
        context = {
            'form': form,
            'post': post,
            'items': items
        }
        return render(
                request,
                'posts/comments.html',
                context
                )
    form.instance.author = request.user
    form.instance.post = post
    form.save()
    return redirect('post', username=username, post_id=post.id)


@login_required
def follow_index(request):
    """
    Функция отрисовки постов автора...

    на которого подписан авторизованный пользователь
    с реализацией паджинатора.
    """
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'posts/follow.html',
        {
            'page': page,
            'paginator': paginator
        }
    )


@login_required
def profile_follow(request, username):
    """Функция подписки на автора."""
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    """Функция отписки пользователя от автора."""
    author = get_object_or_404(User, username=username)
    unfollow = Follow.objects.get(
        user=request.user,
        author=author
    )
    unfollow.delete()
    return redirect('profile', username=username)
