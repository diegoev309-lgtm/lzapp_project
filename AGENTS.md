## Core Commands
- `python manage.py runserver` – start development server
- `python manage.py makemigrations` – create migrations
- `python manage.py migrate` – apply migrations
- `python manage.py test` – run test suite
- `python manage.py createsuperuser` – create admin user
- `python manage.py collectstatic` – collect static files

## Settings
- Settings module: `lzapp.settings`
- Activate virtual environment before installing packages

## Gotchas
- SQLite is used; always run migrations after model changes.
- Run `makemigrations` before `migrate`.
- Tests are executed with `python manage.py test`.
