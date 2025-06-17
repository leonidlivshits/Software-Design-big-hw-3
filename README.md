# Лившиц Леонид Игоревич, БПИ 235

Упрощённая система интернет магазина:

* **API Gateway** на FastAPI
* **Orders Service** на FastAPI + PostgreSQL + RabbitMQ
* **Payments Service** на FastAPI + PostgreSQL + RabbitMQ

Система обеспечивает создание и оплату заказов с поддержкой резервирования средств и асинхронной обработки платежей через шаблон Saga (Transactional Outbox / Inbox).

---

## Технологический стек

* Язык: Python 3.13
* Фреймворк: FastAPI
* Асинхронная база данных: PostgreSQL + SQLAlchemy (Async)
* Сообщения: RabbitMQ (aio-pika)
* Контейнеризация: Docker, docker-compose
* Документация API: OpenAPI (Swagger UI)

---

## Архитектура системы

1. **API Gateway**

   * Прокси и маршрутизация запросов к микросервисам
   * Обеспечивает единый REST-интерфейс для клиента
2. **Payments Service**

   * Создание и пополнение счета
   * Резервирование (hold) и освобождение (release) средств
   * Асинхронная обработка платежных событий (outbox/inbox)
3. **Orders Service**

   * Создание заказов с предварительным резервированием средств
   * Хранение и получение списка заказов
   * Асинхронное обновление статуса заказа по результатам оплаты
4. **RabbitMQ**

   * Очереди `payment_requests` и `payment_results`
   * Обмен событиями между сервисами по шаблону Outbox / Inbox

---

## Установка и настройка

1. Склонировать репозиторий:

   ```bash
   git clone https://github.com/leonidlivshits/Software-Design-big-hw-3.git
   cd Software-Design-big-hw-3
   ```

2. Создать `.env` в корне проекта по аналогии с экзамплом.

3. Активировать виртуальное окружение:
    ```bash
    .venv\Scripts\Activate.ps1
    ```

4. Запустить `docker-compose`:

   ```bash
   docker-compose up --build
   ```

   После старта сервисы будут доступны по следующим адресам:

   * API Gateway: [http://localhost:8000/docs](http://localhost:8000/docs)
   * Orders Service: [http://localhost:8001/docs](http://localhost:8001/docs)
   * Payments Service: [http://localhost:8002/docs](http://localhost:8002/docs)

---

## Описание API

### API Gateway

#### Accounts

* `POST /accounts/{user_id}` - создать счет пользователя
* `POST /accounts/{user_id}/deposit` - пополнить счет, тело `{ "amount": <float> }`
* `POST /accounts/{user_id}/hold` - зарезервировать средства для заказа, тело `{ "order_id": "<UUID>", "amount": <float> }`
* `POST /accounts/{user_id}/release` - отмена резерва, тело `{ "order_id": "<UUID>" }`
* `GET  /accounts/{user_id}` - получить баланс и информацию по счету

#### Orders

* `POST /orders?user_id={user_id}` - создать заказ, тело `{ "amount": <float>, "description": "<строка>" }`
* `GET  /orders?user_id={user_id}` - получить список заказов пользователя
* `GET  /orders/{order_id}?user_id={user_id}` — получить информацию по отдельному заказу

### Взаимодействие между сервисами

1. При создании заказа Gateway проксирует `POST /orders` в Orders Service.
2. Orders Service вызывает зеркально `POST /accounts/{user_id}/hold` в Payments Service для резервирования средств.
3. При успешном hold заказ создаётся в базе Orders Service и публикуется событие `payment_requested` в outbox.
4. Payments Service Inbox-воркер читает `payment_requests`, списывает средства и публикует `payment_succeeded` или `payment_failed` в outbox.
5. Orders Service Result-воркер читает `payment_results` и обновляет статус заказа; в случае `payment_failed` вызывает `release` для снятия hold.

Я не уверен, что это лучшее решение, но как получилось