import json
from django.test import TestCase
from .models import Category, Quote, Tag


class ApiTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Жизнь')
        self.tag = Tag.objects.create(name='Мотивация')
        self.data = {'text': 'Начни сегодня', 'category_id': self.category.pk,
                     'author': 'Автор', 'tag_ids': [self.tag.pk]}

    def send(self, method, url, data):
        return getattr(self.client, method)(url, json.dumps(data), content_type='application/json')

    def create(self):
        response = self.send('post', '/api/quotes/', self.data)
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def test_quote_crud_and_put_patch_difference(self):
        pk = self.create()
        url = f'/api/quotes/{pk}/'
        self.assertEqual(self.client.get(url).json()['tag_ids'], [self.tag.pk])
        self.assertEqual(self.send('patch', url, {'text': 'Новый текст'}).status_code, 200)
        self.assertEqual(self.client.get(url).json()['author'], 'Автор')
        self.assertEqual(self.send('put', url, {'text': 'Замена', 'category_id': self.category.pk}).status_code, 200)
        self.assertEqual(self.client.get(url).json()['author'], '')
        self.assertEqual(self.client.get(url).json()['tag_ids'], [])
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_filter_and_random(self):
        pk = self.create()
        other = Category.objects.create(name='Другая')
        Quote.objects.create(text='Другая цитата', category=other)
        for url in [f'/api/quotes/?tag_id={self.tag.pk}',
                    f'/api/categories/{self.category.pk}/quotes/',
                    f'/api/tags/{self.tag.pk}/quotes/']:
            self.assertEqual([q['id'] for q in self.client.get(url).json()['results']], [pk])
        self.assertEqual(self.client.get(f'/api/quotes/random/?category_id={self.category.pk}&tag_id={self.tag.pk}').json()['id'], pk)
        self.assertEqual(self.client.get(f'/api/quotes/random/?category_id={other.pk}&tag_id={self.tag.pk}').status_code, 404)

    def test_named_resource_crud(self):
        for kind in ['categories', 'tags']:
            url = f'/api/{kind}/'
            created = self.send('post', url, {'name': 'Новое'})
            self.assertEqual(created.status_code, 201)
            detail = created['Location']
            self.assertEqual(self.client.get(detail).status_code, 200)
            self.assertEqual(self.send('put', detail, {'name': 'Изменение'}).status_code, 200)
            self.assertEqual(self.send('patch', detail, {'name': 'Ещё'}).status_code, 200)
            self.assertEqual(self.send('post', url, {'name': 'Ещё'}).status_code, 409)
            self.assertEqual(self.client.delete(detail).status_code, 204)

    def test_tag_changes_and_deletion(self):
        pk = self.create()
        response = self.send('patch', f'/api/quotes/{pk}/', {'tag_ids': []})
        self.assertEqual(response.json()['tag_ids'], [])
        self.send('patch', f'/api/quotes/{pk}/', {'tag_ids': [self.tag.pk]})
        self.assertEqual(self.client.delete(f'/api/tags/{self.tag.pk}/').status_code, 204)
        self.assertTrue(Quote.objects.filter(pk=pk).exists())
        self.assertEqual(self.client.get(f'/api/quotes/{pk}/').json()['tag_ids'], [])
        self.assertEqual(self.client.delete(f'/api/categories/{self.category.pk}/').status_code, 409)

    def test_validation_and_atomicity(self):
        pk = self.create()
        url = f'/api/quotes/{pk}/'
        for data in [{'text': ''}, {'tag_ids': [99999]}, {'category_id': True},
                     {'author': None}, {'unknown': 1}, {'tag_ids': '1'}]:
            self.assertIn(self.send('patch', url, data).status_code, [400, 404])
        self.assertEqual(self.client.get(url).json()['text'], self.data['text'])
        self.assertEqual(self.send('put', url, {'text': 'Без категории'}).status_code, 400)
        self.assertEqual(self.client.post('/api/quotes/', '{', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/api/quotes/', '{}', content_type='text/plain').status_code, 415)
        response = self.client.delete('/api/quotes/')
        self.assertEqual(response.status_code, 405)
        self.assertIn('GET', response['Allow'])
        self.assertEqual(self.client.get('/api/quotes/?tag_id=abc').status_code, 400)
