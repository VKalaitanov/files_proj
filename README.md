<h1 align="center">Инструкция по запуску</h1>

<h3>Подготовка к проекту:</h3>
<p>- создаем проект с виртуальным окружением(python 3.9)</p>
<p>- запускаем Docker на вашем компьютере</p>


<h3>В консоли:</h3>
<p>- клонируете репозиторий в ваш проект: git clone https://github.com/VKalaitanov/files_proj.git</p>
<p>- переходите в директорию проекта: cd files_proj</p>
<p>- запуск проекта в контейнере: docker-compose up --build</p>

<h3>Тестируем:</h3>
<p>- url в браузере: <a href="http://localhost:8000/docs">Жми чтобы перейти</a></p>

<hr>

<h1 align="center">Информация о проекте</h1>

<h3>Технологический стек</h3>
В данной реализации используется следующий технологический стек:
FastAPI: Для создания веб-приложения и обработки HTTP-запросов.
SQLAlchemy: ORM (Object Relational Mapping) для взаимодействия с базой данных SQLite.
SQLite: Легковесная база данных, используемая для хранения информации о файлах.
Pydantic: Для валидации данных, передаваемых в API.
Watchdog: Библиотека для отслеживания изменений в файловой системе, что позволяет автоматически обновлять базу данных при добавлении, изменении или удалении файлов.
Aiofiles: Для асинхронного чтения и записи файлов.
Logging: Модуль для ведения логов, что помогает отслеживать события и ошибки в приложении.
Threading: Для запуска фоновых задач, таких как мониторинг директории.
4. Типовые решения и архитектурные шаблоны
MVC (Model-View-Controller): Хотя в FastAPI нет строго разделения между контроллерами и моделями, концепция MVC применяется в том, что модели представляют структуру данных (например, класс File), а контроллеры (обработчики маршрутов) управляют логикой обработки запросов и взаимодействием с моделями.
RESTful API: Приложение реализует RESTful подход к созданию API, где каждый HTTP-метод соответствует операции (GET, POST, PUT, DELETE) для управления ресурсами (файлами).
Событийно-ориентированная архитектура: Использование библиотеки Watchdog для отслеживания изменений в файловой системе позволяет реагировать на события (например, создание файлов) и выполнять соответствующие действия (например, обновление базы данных).
Фоновая обработка: Фоновая задача, запускаемая в отдельном потоке для мониторинга директории, позволяет приложению оставаться отзывчивым и не блокировать выполнение запросов.
Dependency Injection: FastAPI поддерживает внедрение зависимостей, что позволяет удобно управлять подключениями к базе данных через функцию get_db(), минимизируя дублирование кода.
Валидация данных: Использование Pydantic для валидации входящих и исходящих данных помогает гарантировать, что API принимает только корректные данные, что снижает вероятность ошибок и уязвимостей.
Асинхронность: Применение асинхронного программирования с использованием async и await для работы с файлами позволяет улучшить производительность приложения, особенно при работе с вводом-выводом.
Эти решения помогают создать стабильное, масштабируемое и удобное в использовании приложение для управления файлами.
