# Change log
All notable changes to this project will be documented in this file.

# WWW-Authenticate header

When authentication fails, Eve sets the following header in response:

```
WWW-Authenticate: Basic realm="eve"
```
This caused some browsers to show a user name/password dialog
impacting our UI. Ideally, the authentication scheme in this header
should be set based on the type of authentication that is being
used. For example, if "TokenAuth" is used, the scheme should be
"Bearer". But for now, we are hardcoding "Bearer".

Commit ID: 70a18e6f96287d2643a9d23e77174e9bb7526287.

# 2021-07-30
### Disable concurrency check for DELETE method.
In most cases, the DELETE operation is called when we are sure that the resource needs to be deleted.
Hence, there is no point to check for the ETags. The DELETE can now be called without the "If-Match"
header set.

Commit: [`2fd2d9eff51ae2185d7c44bc1180e4e165b7019a`](https://github.com/catalogicsoftware/eve/commit/2fd2d9eff51ae2185d7c44bc1180e4e165b7019a)

# 2021-07-15
### Support "include_user_id" query parameter for PATCH method.
If the PATCH operation is successful, a full resource will be returned. We added support
for the "include_user_id" query parameter, so if it is set, the returned resource will
contain the value of "auth_field".

Commit: [`8b6c22cfe4ef61f83b06efbba02375440da22c12`](https://github.com/catalogicsoftware/eve/commit/8b6c22cfe4ef61f83b06efbba02375440da22c12)

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
