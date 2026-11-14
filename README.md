# dop — REST API цитат на Django

Выполнено **задание №2** с фотографии: цитата по ID; цитаты категории; создание, изменение и удаление цитат; категории и теги; случайная цитата; цитаты с тегом; изменение тегов цитаты.

Только Django и стандартная библиотека Python, без Django REST Framework. SQLite, JSON, GET / POST / PUT / PATCH / DELETE. В условии «puch» принято за PATCH. DELETE нужен для требуемого удаления.

## Запуск

Python 3.10 или новее. Команды выполняются в папке проекта рядом с manage.py.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Linux / macOS / Git Bash:

```bash
# В Git Bash на Windows: source .venv/Scripts/activate
source .venv/bin/activate
```

Затем:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Открыть http://127.0.0.1:8000/api/quotes/ — сначала список пустой. База создаётся командой migrate; чужая база в репозиторий не включена.

## Маршруты

| URL | Методы | Назначение |
|---|---|---|
| `/api/quotes/` | GET, POST | Список / создание цитаты |
| `/api/quotes/ID/` | GET, PUT, PATCH, DELETE | Одна цитата |
| `/api/quotes/random/` | GET | Случайная цитата |
| `/api/categories/` | GET, POST | Список / создание категории |
| `/api/categories/ID/` | GET, PUT, PATCH, DELETE | Категория / переименование / удаление |
| `/api/categories/ID/quotes/` | GET | Все цитаты категории |
| `/api/tags/` | GET, POST | Список / создание тега |
| `/api/tags/ID/` | GET, PUT, PATCH, DELETE | Тег / переименование / удаление |
| `/api/tags/ID/quotes/` | GET | Все цитаты с тегом |

Список и случайная цитата поддерживают `?category_id=1`, `?tag_id=1` или оба фильтра вместе. Пример: `/api/quotes/random/?category_id=1&tag_id=1`. ID обозначает числовой идентификатор, фактические значения берутся из ответов POST.

POST цитаты: обязательны `text`, `category_id`; `author` и `tag_ids` необязательны. PUT заменяет состояние: обязательны `text`, `category_id`, пропущенные `author` и `tag_ids` сбрасываются в пустые. PATCH изменяет только переданные поля. Для категории и тега используется поле `name`.

## Примеры запросов

В Git Bash / Linux / macOS — curl, в Windows PowerShell используйте curl.exe либо Postman с Body → raw → JSON и заголовком Content-Type: application/json.

```bash
# 1. Создать категорию и тег. В новой базе они получат ID 1.
curl -X POST http://127.0.0.1:8000/api/categories/ -H 'Content-Type: application/json' -d '{"name":"Жизнь"}'
curl -X POST http://127.0.0.1:8000/api/tags/ -H 'Content-Type: application/json' -d '{"name":"Мотивация"}'

# 2. Создать цитату.
curl -X POST http://127.0.0.1:8000/api/quotes/ -H 'Content-Type: application/json' -d '{"text":"Начни сегодня","author":"Неизвестен","category_id":1,"tag_ids":[1]}'

# 3. Получить по ID и выбрать случайную по тегу.
curl http://127.0.0.1:8000/api/quotes/1/
curl 'http://127.0.0.1:8000/api/quotes/random/?tag_id=1'

# 4. Полностью заменить цитату.
curl -X PUT http://127.0.0.1:8000/api/quotes/1/ -H 'Content-Type: application/json' -d '{"text":"Новый текст","author":"Автор","category_id":1,"tag_ids":[1]}'

# 5. Изменить только теги. [] убирает все теги, [1,2] заменяет набор.
curl -X PATCH http://127.0.0.1:8000/api/quotes/1/ -H 'Content-Type: application/json' -d '{"tag_ids":[]}'

# 6. Переименовать тег и удалить цитату.
curl -X PATCH http://127.0.0.1:8000/api/tags/1/ -H 'Content-Type: application/json' -d '{"name":"Вдохновение"}'
curl -X DELETE http://127.0.0.1:8000/api/quotes/1/
```

Ответ цитаты: `{"id":1,"text":"Начни сегодня","author":"Неизвестен","category_id":1,"tag_ids":[1]}`. Список: `{"results":[...]}`. Ошибка: `{"error":"..."}`.

## HTTP и правила

- 200: чтение / изменение; 201 + Location: создание; 204 без тела: удаление.
- 400: неправильные поля / JSON; 404: объект отсутствует или выборка случайной цитаты пуста; 405 + Allow: запрещённый метод; 409: повтор имени или удаление занятой категории; 415: неверный Content-Type.
- Категорию с цитатами удалить нельзя: сначала перенесите или удалите цитаты. Удаление тега сохраняет цитаты и удаляет только связи.
- Запросы без сессий, все изменения атомарны. Случайная цитата выбирается только среди подходящих записей.
- Это локальный учебный API без авторизации; CSRF для JSON-обработчиков отключён. Не публикуйте сервер с этими настройками в интернете. Для реального сервиса нужны авторизация, HTTPS и production-настройки.

## Проверка

```bash
python manage.py check
python manage.py test
```

Тесты проверяют CRUD, PUT и PATCH, категории, теги, фильтры, случайную цитату, ошибки и ограничения удаления.

## Как устроен код

- `quotes/models.py` — Category, Tag, Quote и связи ForeignKey / ManyToManyField.
- `quotes/views.py` — разбор JSON, проверка данных, HTTP-ответы, обработчики API.
- `quotes/urls.py` — маршруты; random расположен раньше числового ID.
- `quotes/migrations/` — создание структуры базы.
- `quotes/tests.py` — тесты на встроенном Django TestCase.
- `config/` — настройки проекта; `manage.py` — команды Django.
