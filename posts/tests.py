import datetime as dt
import os
import shutil

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post, User


class ContentTest(TestCase):
    """Набор тестов профиля и страницы постов."""

    def setUp(self):
        """Задаю двух пользователей.

        Одного авторизую, другой остаётся без авторизации.
        """
        self.client_auth = Client()
        self.client_unauth = Client()
        self.user = User.objects.create_user(
            username='tester'
        )
        self.client_auth.force_login(self.user)
        self.group = Group.objects.create(
            title='TestGroup',
            slug='test',
            description='Test group'
        )
        cache.clear()

    def tearDown(self):
        """ЗАметаем следы"""
        try:
            shutil.rmtree('media/cache/')
        except OSError:
            pass

    def test_profile(self):
        """Тест №1 страницы профиля после регистрации."""
        response = self.client_auth.get(
            reverse('profile', args=[self.user.username])
        )
        self.assertEqual(
            response.status_code,
            200,
            msg='Страница пользователя не создаётся'
            )

    def test_new_post_authorized(self):
        """Тест №2 публикации поста авторизованным пользователем."""
        new_post = self.client_auth.get(reverse('new_post'), follow=True)
        self.assertEqual(
            new_post.status_code,
            200,
            msg='Авторизованный пользователь не может создать пост'
        )

        new_post = self.client_auth.post(
            reverse('new_post'),
            {
                'text': 'Новый пост',
                'group': self.group.id}
        )
        """Проверяю изменение количества постов после создания в бд."""
        self.assertEqual(
            Post.objects.count(),
            1,
            msg='Пост не создаётся'
        )

        """Проверяю соответствие текста, автора и группы с заданными. """
        post = Post.objects.first()
        self.assertEqual(
            post.text,
            'Новый пост',
            msg='Текст не совпадает'
        )
        self.assertEqual(
            post.author,
            self.user,
            msg='Автор не совпадает'
        )
        self.assertEqual(
            post.group,
            self.group,
            msg='Группа не совпадает'
        )

    def test_new_post_unauthorized(self):
        """Тест №3 невозможности создания нового поста без авторизации."""
        new_post = self.client_unauth.post(
            reverse('new_post'),
            {
                'text': 'Новый тестовый пост незалогиненного пользователя',
                'group': self.group.id}
        )
        new_post = self.client_unauth.get(reverse('new_post'), follow=True)
        self.assertRedirects(
            new_post,
            '%s?next=%s' % (reverse('login'), reverse('new_post'),
                            ),
            msg_prefix='Пользователя не перенаправляет на страницу логина'
        )
        self.assertEqual(
            Post.objects.count(),
            0,
            msg='Незалогиненный пользователь создал пост'
        )

    def test_post_publish(self):
        """Тест №4 отображения поста на главной, странице профиля...

        и странице поста.
        """
        self.post = Post.objects.create(
            text='Тестовый пост',
            author=self.user,
            pub_date=dt.datetime.now(),
            group=self.group
        )
        """Отображение записи на главной странице
        и на странице профиля пользователя.
        """
        url_list = (
            reverse('index'),
            reverse('profile', args=[self.user])
        )
        for url in url_list:
            with self.subTest(url=url):
                response = self.client_auth.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    msg='Главная страница не отображается'
                    )
                counter = response.context['paginator'].count
                self.assertEqual(
                    counter,
                    1,
                    msg='На странице неверное количество записей'
                )
                self.assertEqual(
                    response.context['page'][0].text,
                    self.post.text,
                    msg='Текст не совпадает с заданным'
                    )
                self.assertEqual(
                    response.context['page'][0].group,
                    self.group,
                    msg='Название группы не совпадает с заданной'
                )
                self.assertEqual(
                    response.context['page'][0].author,
                    self.post.author
                )

        """Отображение записи на странице самой записи."""
        post = self.client_auth.get(
            reverse(
                'post', args=[self.post.author, Post.objects.first().id]
                ),
            follow=True
        )
        self.assertEqual(
            post.status_code,
            200,
            msg='Страница поста не отображается'
        )
        self.assertEqual(
            post.context['post'].text,
            self.post.text,
            msg='Текст не совпадает с заданным'
        )
        self.assertContains(
            post,
            self.post,
            msg_prefix='Запись не найдена'
        )

    def test_post_edit_authorized(self):
        """Тест №5 редактирования поста авторизованным пользователем.

        Попутно проверка изменённого поста на всех связанных страницах.
        """
        self.post = Post.objects.create(
            text='Тестовый пост',
            author=self.user,
            pub_date=dt.datetime.now(),
            group=self.group
        )
        self.new_group = Group.objects.create(
            title='NewTestGroup',
            slug='newtest',
            description='New test group'
        )
        self.client_auth.post(
            reverse('post_edit',
                    args=[self.user.username, self.post.id]
                    ),
            {
                'text': 'Отредактированный тестовый пост',
                'pub_date': dt.datetime.now(),
                'group': self.new_group.id}
        )
        """Отображение отредактированного поста на главной странице,
        на странице профиля пользователя и странице группы"""
        url_list = (
            reverse('index'),
            reverse('profile', args=[self.user]),
            reverse('group_posts', args=[self.new_group.slug])
        )
        for url in url_list:
            with self.subTest(url=url):
                response = self.client_auth.get(url)
                self.assertEqual(
                    response.status_code,
                    200,
                    msg='Главная страница не отображается'
                )
                counter = response.context['paginator'].count
                self.assertNotEqual(
                    counter,
                    0,
                    msg='На странице неправильное количество записей'
                )
                self.assertEqual(
                    response.context['page'][0].text,
                    'Отредактированный тестовый пост',
                    msg='Текст не совпадает с заданным'
                )
                self.assertEqual(
                    response.context['page'][0].group,
                    self.new_group,
                    msg='Название группы не совпадает с заданным'
                )
                self.assertEqual(
                    response.context['page'][0].author,
                    self.user,
                    msg='Имя автора неверное'
                )

        """Так как группа сменилось, так же проверка на удаление записи
        со страницы прошлой группы.
        """
        old_group_response = self.client_auth.get(
            reverse('group_posts', args=[self.group.slug])
        )
        msg = 'Запись всё ещё пренадлежит прошлой группе'
        self.assertEqual(
                old_group_response.status_code,
                200,
                msg='Главная страница не отображается'
        )
        counter = old_group_response.context['paginator'].count
        self.assertEqual(
                counter,
                0,
                msg=msg
        )
        self.assertNotContains(
                old_group_response,
                'Отредактированный тестовый пост',
                msg_prefix=msg
        )

        """Отображение отредактированной записи на странице самой записи."""
        post = self.client_auth.get(
            reverse('post', args=[self.user.username, 1]),
            follow=True
        )
        self.assertEqual(
            post.status_code,
            200,
            msg='Страница поста не отображается'
        )
        self.assertEqual(
            post.context['post'].text,
            'Отредактированный тестовый пост',
            msg='Текст не совпадает с заданным'
        )


class TestImg(TestCase):
    """Тесты на наличие картинок на страницах."""

    def setUp(self):
        """Задаю пользователя, авторизую его."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='tester'
        )
        self.client.force_login(self.user)
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Группа для теста'
        )
        cache.clear()

    def tearDown(self):
        """Заметаем следы"""
        try:
            os.remove('media/posts/gif')
            shutil.rmtree('media/cache/')
        except OSError:
            pass

    def test_post_img(self):
        """Тест шаблона на наличие тэга <img>."""
        gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile(
            name='gif',
            content=gif,
            content_type='image/gif',
        )
        post = Post.objects.create(
            text='Тестовый пост',
            author=self.user,
            pub_date=dt.datetime.now(),
            group=self.group,
            image=img
        )
        url_list = [
            reverse('index'),
            reverse('profile', args=[self.user.username]),
            reverse('post', args=[self.user.username, post.id]),
            reverse('group_posts', args=[self.group.slug])
        ]

        for url in url_list:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, '<img')

    def test_not_grafic_img(self):
        """Тест защиты от загрузки не-графических файлов."""
        not_jpeg = SimpleUploadedFile(
            name='jpeg',
            content=b'content',
            content_type='image/jpeg',
        )
        url = reverse('new_post')
        response = self.client.post(
                    url,
                    {
                        'text': 'Какой то текст',
                        'group': self.group.id,
                        'image': not_jpeg
                    },
                    follow=True
        )
        self.assertFormError(
                response,
                'form',
                'image',
                errors=('Загрузите правильное изображение. '
                        'Файл, который вы загрузили, поврежден '
                        'или не является изображением.')
                    )


class TestCache(TestCase):
    """Тест кэширования главной страницы."""

    def setUp(self):
        """Создание пользователя и поста."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='tester'
        )
        self.client.force_login(self.user)
        self.group = Group.objects.create(
            title='TestingGroup',
            slug='Test',
            description='Группа для теста'
        )
        self.post = Post.objects.create(
            text='Тестовый пост',
            author=self.user,
            pub_date=dt.datetime.now(),
            group=self.group
        )

    def tearDown(self):
        """ЗАметаем следы"""
        try:
            shutil.rmtree('media/cache/')
        except OSError:
            pass

    def test_cache(self):
        """Тест кэширования главной страницы."""
        response = self.client.get(reverse('index'))
        self.client.post(
            reverse('new_post'),
            {
                'text': 'Новый тестовый пост',
                'group': self.group.id
            }
        )
        self.assertContains(
            response,
            self.post.text,
            msg_prefix='Пост не отображается'
        )
        self.assertNotContains(
            response,
            'Новый тестовый пост',
            msg_prefix='Ошибка кэширования, новый пост отобразился сразу'
        )
        self.assertEqual(
            response.context['paginator'].count,
            1,
            msg='Количество постов на странице изменилось'
                'до очистки кэша'
        )

        cache.clear()
        new_response = self.client.get(reverse('index'))
        self.assertContains(
            new_response,
            'Новый тестовый пост',
            msg_prefix='Кэш работает неверно, новый пост не отобразился'
        )
        self.assertEqual(
            new_response.context['paginator'].count,
            2,
            msg='Новый пост не создался'
        )


class FollowTest(TestCase):
    """Совокупность тестов подписки и отписки."""

    def setUp(self):
        """Описываю двух пользователей.

        Подписчика и автора.
        """
        self.client = Client()
        self.user_follower = User.objects.create_user(
            username='tester_follower'
        )
        self.user_following = User.objects.create_user(
            username='tester_following'
        )
        self.client.force_login(self.user_follower)
        self.group = Group.objects.create(
            title='TestingGroup',
            slug='Test',
            description='Группа для теста'
        )
        self.post = Post.objects.create(
            text='Тестовый пост',
            author=self.user_following,
            pub_date=dt.datetime.now(),
            group=self.group
        )
        cache.clear()

    def tearDown(self):
        """ЗАметаем следы"""
        try:
            shutil.rmtree('media/cache/')
        except OSError:
            pass

    def test_follow(self):
        """Тест подписки."""
        response = self.client.post(
            reverse(
                'profile_follow',
                args=[self.user_following]
            ),
            follow=True
        )
        self.assertEqual(
            response.status_code,
            200,
            msg='Страница подписки не отображается')
        self.assertEqual(
            Follow.objects.count(),
            1,
            msg='Функция подписки работает не корректно')
        follow_pair = Follow.objects.first()
        self.assertEqual(
            follow_pair.user,
            self.user_follower,
            msg='Проверь функцию подписки, подписчик не указан'
        )
        self.assertEqual(
            follow_pair.author,
            self.user_following,
            msg='Проверь функцию подписки, автор не указан'
        )

    def test_unfollow(self):
        """Тест отписки."""
        Follow.objects.create(
            author=self.user_following,
            user=self.user_follower
        )
        response = self.client.post(
            reverse(
                'profile_unfollow',
                args=[self.user_following.username]
            ),
            follow=True
        )
        self.assertEqual(
            response.status_code,
            200,
            msg='Страница отписки не отображается')
        self.assertEqual(
            Follow.objects.count(),
            0,
            msg='Функция отписки работает не корректно.')

    def test_follower_index(self):
        """Проверка верной работы вкладки избранных авторов при подписке."""
        self.client.post(
            reverse(
                'profile_follow',
                args=[self.user_following]
            ),
            follow=True
        )
        response = self.client.get(
            reverse('follow_index')
        )
        counter = response.context['paginator'].count
        self.assertEqual(
            counter,
            1,
            msg='На странице неправильное количество записей'
        )
        context = response.context['page'][0]
        self.assertEqual(
            context.text,
            self.post.text,
            msg='Пост на странице подписчика не отображается'
        )
        self.assertEqual(
            context.author,
            self.user_following,
            msg='Имя автора не соответствует ожидаемому'
        )
        self.assertEqual(
            context.group,
            self.group,
            msg='Название группы не совпадает с заданным'
        )

    def test_not_follower_index(self):
        """Проверка верной работы вкладки избранных авторов при отписке."""
        response = self.client.get(
            reverse('follow_index')
        )
        msg = 'Пост отображается при отсуствии подписки на автора'
        counter = response.context['paginator'].count
        self.assertEqual(
            counter,
            0,
            msg=msg
        )
        self.assertNotContains(
            response,
            self.post.text,
            msg_prefix=msg
        )


class CommentTest(TestCase):
    """Тест комментариев."""

    def setUp(self):
        """По аналогии с тестом профиля и постов...

        создаю двух пользователей. Залогиненого и не совсем.
        """
        self.client_auth = Client()
        self.client_unauth = Client()
        self.user = User.objects.create_user(
            username='tester'
        )
        self.client_auth.force_login(self.user)
        self.group = Group.objects.create(
            title='TestGroup',
            slug='test',
            description='Test group'
        )
        cache.clear()

    def tearDown(self):
        """ЗАметаем следы"""
        try:
            shutil.rmtree('media/cache/')
        except OSError:
            pass

    def test_auth_comment(self):
        """Авторизованный пользователь...

        имеет возможность оставить комментарий.
        """
        self.post = Post.objects.create(
            text='Тестовый пост авторизованного пользователя',
            author=self.user,
            pub_date=dt.datetime.now(),
            group=self.group
        )
        self.client_auth.post(
            reverse(
                'add_comment',
                args=[
                    self.user.username,
                    self.post.id
                ]
            ),
            {
                'text': 'Тестовый коммент'
            }
        )
        msg = 'Комментарий не добавляется'
        self.assertEqual(
            Comment.objects.count(),
            1,
            msg=msg
        )
        comment = Comment.objects.first()
        self.assertEqual(
            comment.text,
            'Тестовый коммент',
            msg=msg
        )
        self.assertEqual(
            comment.author,
            self.user,
            msg=msg
        )

        response = self.client.get(
            reverse(
                'post',
                args=[self.post.author, Post.objects.first().id]),
            follow=True
        )
        response_comment = response.context['items'].first()
        self.assertEqual(
            response_comment.text,
            comment.text,
            msg='Текст комментария не совпадает с заданным'
        )
        self.assertEqual(
            response_comment.author,
            comment.author,
            msg='Автор комментария не совпадает с заданным'
        )

    def test_unauth_comment(self):
        """Неавторизованный пользователь...

        не имеет возможности оставить комментарий.
        """
        self.post = Post.objects.create(
            text='Тестовый пост авторизованного пользователя',
            author=self.user,
            pub_date=dt.datetime.now(),
            group=self.group
        )
        self.client_unauth.post(
            reverse(
                'add_comment',
                args=[
                    self.user.username,
                    self.post.id
                ]
            ),
            {
                'text': 'Тестовый пост, которого не должно быть'
            }
        )
        self.assertEqual(
            Comment.objects.count(),
            0,
            msg='Авторизованный пользователь написал комментарий.'
                'Проверь функцию создания комментария.'
        )
