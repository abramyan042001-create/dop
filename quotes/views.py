"""JSON API без Django REST Framework. Используются только Django и стандартная библиотека."""
import json
import random
from functools import wraps

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Category, Quote, Tag


class ApiError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def endpoint(methods):
    def decorate(view):
        @csrf_exempt
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                response = JsonResponse({"error": "Метод не поддерживается"}, status=405)
                response["Allow"] = ", ".join(methods)
                return response
            try:
                # Любая ошибка откатывает изменения, в том числе связи с тегами.
                with transaction.atomic():
                    return view(request, *args, **kwargs)
            except ApiError as error:
                return JsonResponse({"error": error.message}, status=error.status)
            except ProtectedError:
                return JsonResponse({"error": "Категория содержит цитаты"}, status=409)
            except IntegrityError:
                return JsonResponse({"error": "Такое имя уже существует"}, status=409)
            except ValidationError as error:
                return JsonResponse({"error": error.messages}, status=400)
        return wrapped
    return decorate


def body(request, allowed):
    if request.content_type != "application/json":
        raise ApiError("Ожидается Content-Type: application/json", 415)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise ApiError("Некорректный JSON")
    if not isinstance(data, dict) or set(data) - set(allowed):
        raise ApiError("Ожидается объект JSON только с разрешёнными полями")
    return data


def find(model, pk):
    try:
        return model.objects.get(pk=pk)
    except model.DoesNotExist:
        raise ApiError("Объект не найден", 404)


def positive_id(value):
    if type(value) is not int or value < 1:
        raise ApiError("ID должен быть положительным целым числом")
    return value


def nonempty(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ApiError(f"Поле {field} должно быть непустой строкой")
    return value.strip()


def serialize(quote):
    return {"id": quote.pk, "text": quote.text, "author": quote.author,
            "category_id": quote.category_id,
            "tag_ids": sorted(tag.pk for tag in quote.tags.all())}


def filtered(request, category_id=None, tag_id=None):
    query = Quote.objects.select_related("category").prefetch_related("tags")
    for field, nested in (("category_id", category_id), ("tag_id", tag_id)):
        value = nested if nested is not None else request.GET.get(field)
        if value is not None:
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ApiError(f"Некорректный {field}")
            positive_id(value)
            find(Category if field == "category_id" else Tag, value)
            query = query.filter(**({"category_id": value} if field == "category_id" else {"tags__id": value}))
    return query.distinct()


def save_quote(request, quote=None):
    data = body(request, ["text", "author", "category_id", "tag_ids"])
    full = quote is None or request.method == "PUT"
    if full and not {"text", "category_id"} <= data.keys():
        raise ApiError("Обязательные поля: text, category_id")
    quote = quote or Quote()
    if "text" in data:
        quote.text = nonempty(data["text"], "text")
    if "author" in data or full:
        author = data.get("author", "")
        if not isinstance(author, str):
            raise ApiError("author должен быть строкой")
        quote.author = author
    if "category_id" in data:
        quote.category = find(Category, positive_id(data["category_id"]))
    tags = None
    if "tag_ids" in data or full:
        ids = data.get("tag_ids", [])
        if not isinstance(ids, list):
            raise ApiError("tag_ids должен быть массивом ID")
        tags = [find(Tag, positive_id(pk)) for pk in ids]
    quote.full_clean()
    quote.save()
    if tags is not None:
        quote.tags.set(tags)
    return quote


@endpoint(["GET", "POST"])
def quotes(request):
    if request.method == "GET":
        return JsonResponse({"results": [serialize(q) for q in filtered(request)]})
    quote = save_quote(request)
    response = JsonResponse(serialize(quote), status=201)
    response["Location"] = f"/api/quotes/{quote.pk}/"
    return response


@endpoint(["GET", "PUT", "PATCH", "DELETE"])
def quote_detail(request, pk):
    quote = find(Quote, pk)
    if request.method == "DELETE":
        quote.delete()
        return HttpResponse(status=204)
    if request.method != "GET":
        quote = save_quote(request, quote)
    return JsonResponse(serialize(quote))


@endpoint(["GET"])
def random_quote(request):
    query = filtered(request)
    ids = list(query.values_list("id", flat=True))
    if not ids:
        raise ApiError("Нет подходящих цитат", 404)
    return JsonResponse(serialize(query.get(pk=random.choice(ids))))


@endpoint(["GET"])
def related_quotes(request, category_id=None, tag_id=None):
    return JsonResponse({"results": [serialize(q) for q in filtered(request, category_id, tag_id)]})


def named_resource(model):
    @endpoint(["GET", "POST"])
    def collection(request):
        if request.method == "GET":
            return JsonResponse({"results": list(model.objects.order_by("id").values("id", "name"))})
        data = body(request, ["name"])
        obj = model(name=nonempty(data.get("name"), "name"))
        obj.full_clean(validate_unique=False)
        obj.save()
        response = JsonResponse({"id": obj.pk, "name": obj.name}, status=201)
        response["Location"] = f"/api/{'categories' if model is Category else 'tags'}/{obj.pk}/"
        return response

    @endpoint(["GET", "PUT", "PATCH", "DELETE"])
    def detail(request, pk):
        obj = find(model, pk)
        if request.method == "DELETE":
            obj.delete()
            return HttpResponse(status=204)
        if request.method != "GET":
            data = body(request, ["name"])
            if request.method == "PUT" or "name" in data:
                obj.name = nonempty(data.get("name"), "name")
                obj.full_clean(validate_unique=False)
                obj.save()
        return JsonResponse({"id": obj.pk, "name": obj.name})
    return collection, detail


categories, category_detail = named_resource(Category)
tags, tag_detail = named_resource(Tag)
