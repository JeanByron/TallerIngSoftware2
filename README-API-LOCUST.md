# API Laravel 9 — Laboratorio Locust

API REST para practicar pruebas de **carga**, **estrés** y **capacidad** con [Locust](https://locust.io/).

## Requisitos

- PHP 8.0+
- Composer
- MySQL o PostgreSQL (recomendado para 1.5M registros)
- Extensión PHP correspondiente (`pdo_mysql` / `pdo_pgsql`)

## Instalación

```bash
cd laravel-api
composer install
cp .env.example .env   # si aplica
php artisan key:generate
```

Configure la base de datos en `.env`:

```env
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=locust_lab
DB_USERNAME=root
DB_PASSWORD=
```

```bash
php artisan migrate:fresh --seed
```

Eso ejecuta `DatabaseSeeder`, que llama a `MassUserSeeder` (1.500.000 usuarios por defecto).

Opcional en `.env`:

```env
MASS_USER_SEED_COUNT=1500000
MASS_USER_CHUNK_SIZE=2000
```

Alternativa sin borrar tablas:

```bash
php artisan users:seed-mass --count=1500000 --chunk=2000
```

El seed masivo puede tardar varios minutos según el hardware. Ajuste `MASS_USER_CHUNK_SIZE` o `--chunk` si hay errores de memoria.

## Endpoints (versión entregada — sin paginación)

Base URL: `http://HOST:PUERTO/api`

Los tres GET usan `User::all()` (en `over-twenty` se filtra en memoria tras cargar todo). Devuelven un arreglo JSON con todos los registros. Con 1.5M filas provoca timeouts, 500 por memoria o respuestas enormes. **Es intencional:** parte del laboratorio es corregirlo.

| Método | Ruta | Comportamiento actual |
|--------|------|------------------------|
| GET | `/users` | `User::all()` |
| GET | `/users/emails` | `User::all(['id', 'email'])` |
| GET | `/users/over-twenty` | `User::all()` + filtro en PHP por edad |
| POST | `/users/bulk` | Crea **exactamente 3** usuarios (sin cambios) |

Archivo a modificar: `app/Http/Controllers/Api/UserController.php`.

### Tarea API (estudiantes)

1. Sustituir `->get()` por `->paginate()` (o cursor pagination) en los tres GET.
2. Exponer `?page=` y `?per_page=` con límites razonables (p. ej. máx. 200).
3. Documentar en el informe el antes/después (una petición con dataset pequeño basta para demo funcional).
4. **Después** de paginar, ejecutar Locust con el seed masivo.

### Ejemplo GET usuarios (estado actual)

```http
GET /api/users HTTP/1.1
Host: localhost:8000
Accept: application/json
```

Respuesta: arreglo JSON con un objeto por usuario (todos los campos visibles del modelo, sin contraseña).

### Ejemplo POST bulk (3 usuarios)

```http
POST /api/users/bulk HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Accept: application/json

{
  "users": [
    {
      "name": "Ana López",
      "email": "ana.locust@example.com",
      "birth_date": "1998-05-12"
    },
    {
      "name": "Bruno Díaz",
      "email": "bruno.locust@example.com",
      "birth_date": "2000-11-03",
      "password": "secreto123"
    },
    {
      "name": "Carla Ruiz",
      "email": "carla.locust@example.com",
      "birth_date": "1995-01-20"
    }
  ]
}
```

Respuesta `201` con los tres usuarios creados (sin contraseña en JSON).

## Factory (datos pequeños)

```bash
php artisan tinker
>>> \App\Models\User::factory(100)->create();
```

La factory genera `birth_date` aleatoria entre 10 y 70 años atrás.

## Servidor de desarrollo

```bash
php artisan serve --host=0.0.0.0 --port=8000
```

Para pruebas de carga reales, use PHP-FPM + Nginx/Apache y OPcache en un entorno dedicado, no el servidor embebido de `artisan serve`.

## Tareas para estudiantes

1. **Refactorizar la API:** paginación en los GET de `UserController`.
2. **Locust:** implementar `locustfile.py` con escenarios de carga, estrés y capacidad. Ver `../locust/` y `../overleaf/`.
3. **Informe:** comparar métricas API sin paginar (opcional, dataset pequeño) vs API corregida bajo carga.
