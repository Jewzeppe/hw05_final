from django.test import Client, TestCase


class TestUrl(TestCase):
    """Тест отрисовки страницы 404."""

    def test404(self):
        url = '/foo/g24fds709xcv43l6/'
        self.client = Client()
        response = self.client.get(url)
        self.assertEqual(
            response.status_code,
            404,
            msg='Страница 404 не отображается'
        )
