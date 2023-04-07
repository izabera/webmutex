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

Multiple tests in your CI are running concurrently.  You want to save their
results in some database but you can't be arsed to set one up properly, so you
figure you'll just use a sqlite file and sync it to artifactory, as sqlite can
sort the concurrency aspect out for you.

You proceed to naively wrap each test in

```sh
curl -O $artifactory_url/test_results.db
./build/mytest > test_results.json
./test_result_extractor test_results.json test_results.db
curl -X PUT $artifactory_url --data-binary @test_results.db
```

Now you realise that now each test is running on its own instance of your CI,
so it's grabbing the db and using its own local copy.  There is no concurrency
aspect, and when things get pushed to artifactory they overwrite each other.
You screwed up, _again_, like you always do.  This is why nobody loves you.

Then you figure that not all hope is lost.  You reach this service.  Now you
just need to grab a mutex before fetching your db.

```sh
# reserve a new mutex (only needs to be done once)
curl -X POST https://webmutex.io/reserve > mutex
mutex=$(jq .id < mutex)

# run each test, protect any db updates using the mutex
./build/mytest > test_results.json

while ! curl -f -X POST https://webmutex.io/grab -F "id=$mutex" >mymutex; do
    sleep 1
done

token=$(jq .token < mymutex)

curl -O $artifactory_url/test_results.db
./test_result_extractor test_results.json test_results.db
curl -X PUT $artifactory_url --data-binary @test_results.db

curl -X POST https://webmutex.io/release -F "id=$mutex" -F "token=$token"
```

<style>
    body {margin: 5% auto; background: #f2f2f2; color: #444444; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.8; text-shadow: 0 1px 0 #ffffff; max-width: 73%;}
    code {background: white;}
    a {border-bottom: 1px solid #444444; color: #444444; text-decoration: none;}
    a:hover {border-bottom: 0;}
</style>
