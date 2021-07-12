# Change log
All notable changes to this project will be documented in this file.

# 2021-07-03
### Return user_id in the response, if "include_user_id" query parameter is set.
By default, Eve does not allow the value of "auth_field" to be present in the response.
Hence, we added an optional query parameter, "include_user_id". If set, the user id
will be included in the response. This change will allow getting the owner of a specific
resource without making any additional API requests. This parameter works with the GET operations.

Commit: [`3eb641f4f3a43ac44cd80dee1ecc16669e2c8c0f`](https://github.com/catalogicsoftware/eve/commit/3eb641f4f3a43ac44cd80dee1ecc16669e2c8c0f)

### Allow "auth_field" projection for the POST method.
By default, the "auth_field" projection is disabled for the POST method.
If a blueprint allows only POST method, and inside of that blueprint we try to
use `app.data.find` or `app.data.find_one`, the `force_auth_field_projection` option
will not take any effect. Due to that, we enabled "auth_field" projection for the POST method.

Commit: [`d91bd491858cee0a96b0e630ebaed1daedd1d368`](https://github.com/catalogicsoftware/eve/commit/d91bd491858cee0a96b0e630ebaed1daedd1d368)
