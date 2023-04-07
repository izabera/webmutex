% WebMutex API description

## API

Parameters can be passed as json in the body of the request,
or as http form parameters.

All requests also accept the mutex id via `/request/<id>/`

---

### Grab a mutex: `/grab`

`POST` only

Parameters:

- `id`

If `id` is empty, allocates a new mutex.
Otherwise, tries to grab an existing mutex if it's currently free.

Returns:

- `id`
- `token`
- `status`

---

### Release a mutex: `/release`

`POST` only

Parameters:

- `id`
- `token`

Releases the mutex, using the token received from `/grab`.

Returns:

- `status`

---

### Checks mutex status: `/status`

`GET` and `POST`

Parameters:

- `id`

Releases the mutex, using the token received from `/grab`.

Returns:

- `status`
- `in_use`

---

## Example use

<style>
    body {margin: 5% auto; background: #f2f2f2; color: #444444; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.8; text-shadow: 0 1px 0 #ffffff; max-width: 73%;}
    code {background: white;}
    a {border-bottom: 1px solid #444444; color: #444444; text-decoration: none;}
    a:hover {border-bottom: 0;}
</style>
