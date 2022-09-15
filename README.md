- [AppMap data specification](#appmap-data-specification)
  - [File structure](#file-structure)
    - [version](#version)
    - [metadata](#metadata)
      - [Example](#example)
    - [classMap](#classmap)
      - [Common attributes](#common-attributes)
      - [package and class attributes](#package-and-class-attributes)
      - [function attributes](#function-attributes)
      - [Example](#example-1)
    - [events](#events)
      - [Common attributes](#common-attributes-1)
      - [Common `return` attributes](#common-return-attributes)
      - [Function `call` attributes](#function-call-attributes)
      - [Parameter object format](#parameter-object-format)
      - [Exception object format](#exception-object-format)
      - [Function `return` attributes](#function-return-attributes)
      - [HTTP server request `call` attributes](#http-server-request-call-attributes)
      - [HTTP client request `call` attributes](#http-client-request-call-attributes)
      - [HTTP server response `return` attributes](#http-server-response-return-attributes)
      - [HTTP client response `return` attributes](#http-client-response-return-attributes)
      - [SQL query `call` attributes](#sql-query-call-attributes)
      - [Message `call` attributes](#message-call-attributes)
      - [Example](#example-2)
    - [eventUpdates](#eventupdates)
      - [Example](#example-3)
- [Changelog](#changelog)
  - [v1.8.0](#v180)
  - [v1.7.0](#v170)
  - [v1.6.0](#v160)
  - [v1.5.1](#v151)
  - [v1.5.0](#v150)
  - [v1.4.1](#v141)
  - [v1.4.0](#v140)
  - [v1.3.0](#v130)
  - [v1.2.0](#v120)
  - [v1.1.0](#v110)

# AppMap data specification

The AppMap data specification is a JSON schema that contains
detailed information of an application's runtime code execution, data snapshots
and metadata. This data can be used to visualize and analyze code architecture, design,
and behavior.

This repository serves as the home project for the AppMap data specification. For
more information on the AppMap platform, visit [appmap.io](https://appmap.io).

## File structure

An AppMap file contains a single top level JSON object comprised of the following:
```
{
  "version": <string>,
  "metadata": <object>,
  "classMap": [ <tree of package, class, and function objects> ],
  "events": [ <list of event objects> ],
  "eventUpdates": <object>
}
```

### version

*Required* version number to which the file conforms, such as: `"1.4"`.

See the [Changelog](#changelog) section for version history.

### metadata

*Optional* information about the code from which the AppMap was extracted.

Metadata has the following attributes:

* **name** *Optional* scenario name.
* **labels** *Optional* list of arbitrary labels describing the AppMap.
* **app** *Optional* name of the app to assign to the scenario. The organization to which the app belongs may be specified by separating the organization name and app name by a forward slash `/`. If no organization name is specified, the data is loaded into the user's personal data set. Example of a scoped name: `myorg/myapp`. Example of an unscoped name: `myapp`. The forward-slash character is illegal in app names and org names.
* **language** *Optional* information about the programming language in which code is written.
  * **name** *Required* name of the programming language
  * **engine** *Optional* name of the programming langugae engine, e.g. VM variant.
  * **version** *Required* programming language version
* **frameworks** *Optional* list of frameworks which the code uses.
  * **name** *Required* name of the framework.
  * **version** *Required* version of the framework.
* **client** *Required* information about the AppLand client which recorded the scenario.
  * **name** *Required* short name of the client.
  * **url** *Required* unique URL of the client.
  * **version** *Optional* version of the client.
* **recorder** *Required* information about the method which was used by the client to record the scenario.
  * **name** *Required* name of the recording method. This name must be unique to the client, but need not be unique across different clients.
* **recording** *Optional* information about the entry-point function which was recorded.
  * **defined_class** *Required* name of the class which defines the entry-point function.
  * **method_id** *Required* name of the recorded function.
* **git** *Optional* information about the state of the Git repo.
  * **repository** *Required* repository URL.
  * **branch** *Required* code branch.
  * **commit** *Required* commit identifier.
  * **status** *Required* status of the repo relative to the commit, represented as a list of status messages. If the repo is clean, the status should be an empty list.
  * **tag** *Optional* latest tag.
  * **annotated_tag** *Optional* latest annotated tag.
  * **commits_since_tag** *Optional* number of commits since the last tag.
  * **commits_since_annotated_tag** *Optional* number of commits since the last annotated tag.
* **test_status** *Optional* status of the test that ran to generate the AppMap. Valid values are `succeeded` or `failed`.
* **exception** *Optional* unhandled exception which occurred during scenairo processing.
  * **class** *Required* exception class name.
  * **message** *Optional* exception message.

#### Example

```
{
  "name": "Identity management in the UI permits login with a local password",
  "labels": [ "documentation" ],
  "app": "Discourse",
  "feature": "Login with valid locally managed credentials",
  "feature_group": "Authentication",
  "language": {
    "name": "ruby",
    "engine": "ruby",
    "version": "2.6.2"
  },
  "client": {
    "name": "appmap",
    "url": "https://github.com/applandinc/appmap-ruby",
    "version": "0.21.0"
  },
  "recorder": {
    "name": "rspec"
  },
  "git": {
    "repository": "https://github.com/applandinc/appmap",
    "branch": "master",
    "commit": "c3424f9",
    "status": [
      "M spec/system/feature_spec.rb",
      "M spec/system/user_spec.rb"
    ],
    "annotated_tag": "v1.1.0",
    "commits_since_annotated_tag": "3"
  }
}
```

### classMap

*Required* list of code objects. There are three types of supported objects: `package`, `class`, and `function`.

Note that the terms `package` and `class` are used loosely. In general, they encopass language-specific concepts such as
`directory`, `package`, `class`, `interface`, `module`, etc. Since an AppMap is a high-level representation of code, the
detailed differences between these language-specific concepts aren't usually very important. Rules of thumb:

* Use a `package` for each directory which contains code. A package may contain classes, but not functions.
* Use a `class` for each type declaration in a code file. A class may contain classes and functions, but not packages.

#### Common attributes

Each classMap object has the following attributes:

* **name** *Required* name. Should be the local name of the object, not the fully-scoped name. Example: "User" or
  "show", not "MyApp::User" or "User#show".
* **type** *Required* object type. Must be "package", "class", or "function".

#### package and class attributes

Each "package" and "class" has the following attributes:

* **children** *Optional* List of child objects which are semantically contained.

#### function attributes

Each "function" has the following attributes:

* **location** *Recommended* File path and line number, separated by a colon. Example: "/Users/alice/src/myapp/lib/myapp/main.rb:5".
* **static** *Required* flag if the method is class-scoped (static) or instance-scoped. Must be `true` or `false`. Example: true.
* **labels** *Optional* list of arbitrary labels describing the function.
* **comment** *Optional* documentation comment for the function extracted from the source code.
* **source** *Optional* verbatim source code of the function.

Note if recording several appmaps from the same code base **comment** and
**source** can become widely redundant and contain duplicated data between the
maps. For this reason it might be more convenient to omit them in specific
AppMaps even if available, and instead create a separate AppMap with no
events and just a classmap containing all code encountered in these recordings.

#### Example

```
[
  {
    "name": "appland",
    "type": "package",
    "children": [
      {
        "name": "AppLand",
        "type": "class",
        "children": [
          {
            "name": "Server",
            "type": "class",
            "children": [
              {
                "name": "API",
                "type": "class",
                "children": [
                  {
                    "name": "upload",
                    "location": "/src/architecture/lib/appland/server/api.rb:7",
                    "type": "function",
                    "static": false
                  }
                ]
              },
              {
                "name": "Model",
                "type": "class",
                "children": [
                  {
                    "name": "User",
                    "location": "/src/architecture/lib/appland/server/model.rb:5",
                    "type": "class",
                    "children": [
                      {
                        "name": "create",
                        "location": "/src/architecture/lib/appland/server/model.rb:6",
                        "type": "function",
                        "static": true
                      }
                    ]
                  },
                  {
                    "name": "Scenario",
                    "type": "class",
                    "children": [
                      {
                        "name": "create",
                        "location": "/src/architecture/lib/appland/server/model.rb:11",
                        "type": "function",
                        "static": true
                      },
                      {
                        "name": "review",
                        "location": "/src/architecture/lib/appland/server/model.rb:13",
                        "type": "function",
                        "static": false
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  {
    "name": "active_support",
    "type": "package",
    "children": [
      {
        "name": "ActiveSupport",
        "type": "class",
        "children": [
          {
            "name": "SecurityUtils",
            "type": "class",
            "children": [
              {
                "name": "secure_compare",
                "type": "function",
                "location": "/Users/ajp/.rbenv/versions/2.6.2/lib/ruby/gems/2.6.0/gems/activesupport-6.0.3.2/lib/active_support/security_utils.rb:26",
                "static": true,
                "labels": [
                  "security"
                ]
              }
            ]
          }
        ]
      }
    ]
  }
]
```

### events

*Optional* list of events which were recorded during program execution. Each object in this list is either a function call or a
return from a function call which occurred during an actual program execution.

#### Common attributes

Each event object has the following attributes:

* **id** *Required* unique identifier. Example: 23522.
* **event** *Required* event type. Must be "call" or "return".
* **thread_id** *Required* identifier of the execution thread. Example: 70340688724000.

#### Common `return` attributes

Each "return" event has the following attributes:

* **parent_id** *Required* id of the "call" event corresponding to this "return".
* **elapsed** *Optional* elapsed time in seconds of this function call.


#### Function `call` attributes

A "call" event which represents a function call has the following attributes:

* **defined_class** *Required* name of the class which defines the method. Example: "MyApp::User".
* **method_id** *Required* name of the function which was called in this event. Example: "show".
* **path** *Recommended* path name of the file which triggered the event. Example: "/src/architecture/lib/appland/local/client.rb".
* **lineno** *Recommended* line number which triggered the event. Example: 5.
* **receiver** *Optional* parameter object describing the object on which the function is called. Corresponds to the `receiver`, `self` and `this` concept found in various programming languages.
* **parameters** *Recommended* array of parameter objects describing the function call parameters.
* **static** *Required* flag if the method is class-scoped (static) or instance-scoped. Must be `true` or `false`. Example: true.

**Note**

In order to correlate function call events with function objects defined in the class map, the `path` and
`lineno` attributes of each "call" event should exactly match the `location` attribute of the corresponding `function` in the `classMap`.

#### Parameter object format

Each parameter is an object containing the following attributes:

* **name** *Recommended* name of the parameter. Example: "login".
* **object_id** *Recommended* unique id of the object. Example: 70340693307040
* **class** *Required* fully qualified class or type name of the object. Example: "MyApp::User".
* **value** *Required* string describing the object. This is not a strict JSON serialization, but rather a display
  string which is intended for the user. These strings should be trimmed in length to 100 characters. Example: "MyApp
  user 'alice'"
* **size** *Recommended* number of elements in an array or hash object. Example. "5".
* **properties** *Optional* schema indicating property names and types of hash and hash-like objects. Each entry is a `name` and `class`. Example: "[ {"name": "id", "class": Integer}, {"name": "created_at", "class": Date}]".

#### Exception object format
* **class** *Required* fully qualified class name of the exception. Example: "com.myorg.InvalidUserException"
* **message** *Required* description of the exception cause. Example: "User attribute not defined: 'email'"
* **object_id** *Required* unique id of the object. Example: 70340693307040
* **path** *Optional* path name of the file where the exception was thrown. Example: "/src/main/java/com/myorg/models/User.java".
* **lineno** *Optional* line number where the exception was thrown. Example: 264.

#### Function `return` attributes

A "return" event which represents a function call has the following attributes:

* **return_value** *Optional* object describing the return value. If present, this value uses [parameter object format](#parameter-object-format).
* **exceptions** *Optional* array of exceptions causing this method to exit. If present, this value uses [exception object format](#exception-object-format). When an exception is a wrapper for an underlying `cause`, the cause is the next exception in the `exceptions` array.

#### HTTP server request `call` attributes

A "call" event which represents an HTTP server request will have an `http_server_request` attribute, which is an
object with the following elements:

* **request_method** *Required* HTTP request method. Example: "POST".
* **path_info** *Required* HTTP request path. Example: "/orders/84".
* **normalized_path_info** *Optional* Parameterized request path. When present, each parameter must be formatted as `:param-name`. Example: "/orders/:id".
* **protocol** *Optional* HTTP protocol and version. Example: "HTTP/1.1".
* **headers** *Recommended* an object representing HTTP headers.

See: [HTTP Request-Line](https://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html)

#### HTTP client request `call` attributes

A `call` event which represents an HTTP client request will have an `http_client_request` attribute, which is an
object with the following elements:

* **request_method** _Required_ HTTP request method. Example: `"POST"`.
* **url** _Required_ Request URL, excluding the query string. Example: `"https://website.example/"`.
* **headers** _Recommended_ HTTP headers. Example: `{ "Content-Type": "application/json" }`.

Any query parameters _should_ be passed in the [`message`](#message-call-attributes) attribute of the event.

#### HTTP server response `return` attributes

A `return` event which represents an HTTP server response will have an `http_server_response` attribute, which is an
object with the following elements:

* **status_code** _Required_ HTTP [status code](https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html)
* **headers** _Recommended_ HTTP headers. Example: `{ "Content-Type": "application/json" }`.
* **return_value** _Recommended_ for API routes, the object (e.g. JSON) returned by the method. It's recommended that this `return_value` have the optional `properties` (schema) field.

#### HTTP client response `return` attributes

A `return` event which represents an HTTP client response will have an `http_client_response` attribute, which is an
object with the following elements:

* **status_code** _Required_ HTTP [status code](https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html)
* **headers** _Recommended_ an object representing HTTP headers of the response.
* **return_value** _Recommended_ for API routes, the object (e.g. JSON) returned by the method. It's recommended that this `return_value` have the optional `properties` (schema) field.

#### SQL query `call` attributes

A "call" event which represents a SQL query will have an `sql_query` attribute, which is an
object with the following elements:

* **database_type** *Required* name of the database. Example: "postgresql".
* **sql** *Required* SQL query string.
* **explain_sql** *Optional* query plan provided by the database engine.
* **server_version** *Optional* database server version.

#### Message `call` attributes

A "call" event which represents the receipt of a message will have a `message` attribute, which
is a list of objects in [parameter object format](#parameter-object-format). `message` is also used in
`http_client_request` and `http_server_request` to indicate parameters.

#### Example

```
[
  {
    "id": 1,
    "event": "call",
    "defined_class": "AppLand::Local::Client",
    "method_id": "install",
    "path": "/src/architecture/lib/appland/local/client.rb",
    "lineno": 5,
    "static": true,
    "thread_id": 70340688724000,
    "receiver": {
      "name": "self"
      "class": "Module",
      "value": "AppLand::Local::Client",
      "object_id": 70340693307040
    },
    "parameters": [
      "name": "name"
      "class": "String",
      "value": "ruby",
      "object_id": 70340689027780
    ]
  },
  {
    "id": 2,
    "event": "return",
    "return_value": {
      "class": "Class",
      "value": "AppLand::Local::Client::Ruby",
      "object_id": 70340693343340
    },
    "parent_id": 1,
    "elapsed": 7.2e-05
  },
  {
    "id": 3,
    "event": "call",
    "defined_class": "AppLand::Local::UI::UI",
    "method_id": "initialize",
    "path": "/src/architecture/lib/appland/local/ui.rb",
    "lineno": 39,
    "static": false,
    "thread_id": 70340688724000,
    "receiver": {
      "name": "self"
      "class": "AppLand::Local::UI::UI",
      "value": "#<struct AppLand::Local::UI::UI visualizations=nil>",
      "object_id": 70340689072680
    },
    "parameters": [
      "name": "visualizations"
      "class": "Array",
      "value": "[AppLand::Local::UI::Component::Timeline, AppLand::Local::UI::Component::CallStack, AppLand::Local::",
      "object_id": 70340693502240
    ]
    }
  },
  {
    "id": 4,
    "event": "return",
    "return_value": {
      "class": "NilClass",
      "value": null,
      "object_id": 8
    },
    "parent_id": 3,
    "elapsed": 3.0e-06
  },
  {
    "id": 5,
    "event": "call",
    "defined_class": "AppLand::Local::Client",
    "method_id": "client",
    "path": "/src/architecture/lib/appland/local/client.rb",
    "lineno": 9,
    "static": true,
    "thread_id": 70340688724000,
    "receiver": {
      "name": "self"
      "class": "Module",
      "value": "AppLand::Local::Client",
      "object_id": 70340693307040
    },
    "parameters": []
  },
  {
    "id": 6,
    "event": "return",
    "exceptions": [
      {
        "class": "ClientValidationError",
        "message": "The client failed validation",
        "path": "/src/architecture/lib/appland/local/client.rb",
        "lineno": 8,
        "object_id": 70340693343340
      }
    ],
    "parent_id": 5,
    "elapsed": 2.0e-06
  }
]
```
### eventUpdates
*Optional* Object containing events that were updated after they were added to the AppMap. The name
of each attribute is the `id` of the updated event. The value of the attribute is an `event` object
that should be used in place of the original event.
#### Example
```
{
  ...
  "events": [
    ...
    {
      "event": "call",
      "http_server_request": {
        "headers": {
          "host": "localhost:8080",
          "user-agent": "curl/7.79.1",
          "accept": "application/json"
        },
        "path_info": "/owners/1/pets/1/edit",
        "protocol": "HTTP/1.1",
        "request_method": "GET"
      },
      "id": 172,
      "thread_id": 182
    },
    ...
  ]
  ...
  "eventUpdates": {
    "172": {
      "event": "call",
      "http_server_request": {
        "headers": {
          "host": "localhost:8080",
          "user-agent": "curl/7.79.1",
          "accept": "application/json"
        },
        "normalized_path_info": "/owners/:ownerId/pets/:petId/edit",
        "path_info": "/owners/1/pets/1/edit",
        "protocol": "HTTP/1.1",
        "request_method": "GET"
      },
      "id": 172,
      "message": [
        {
          "class": "java.lang.String",
          "kind": "req",
          "name": "petId",
          "object_id": 836791441,
          "value": "1"
        },
        {
          "class": "java.lang.String",
          "kind": "req",
          "name": "ownerId",
          "object_id": 1966623949,
          "value": "1"
        }
      ],
      "thread_id": 182
    },
    ...
  ],
  ...
}
```
# Changelog

## v1.8.0
* Add `eventUpdates`.
## v1.7.0

* Add recommended `size` field to parameter object.
* Add optional `properties` field to parameter object.
* Add optional `return_value` to `http_client_response` and `http_server_response`.

## v1.6.0

* Add optional `test_status` and `exception` fields in metadata for conveying the test status.
* Add HTTP request and response headers, as implemented by appmap-ruby.
* Relax requirements on parameter objects.

## v1.5.1

* Specify format for parameters in `normalized_path_info`.

## v1.5.0

* Added `http_client_request` and `http_client_response`.

## v1.4.1

* Make source location optional; it's not always possible to provide it but appmaps lacking it can still be useful.
* Make receiver and parameters optional; they not always make sense and there could be performance
  or operational reasons to skip capture.

## v1.4.0

* Added `normalized_path_info` to HTTP server request object.
* Clarify required attributes for function `call` events, as compared to common attributes for all `call` events.

## v1.3.0

* Added `comment` and `source` to a `function` entry in the classmap.

## v1.2.0

* Added `labels` to a `function` entry in the classmap.
* Moved `static`, `defined_class`, `method_id`, `path`, `lineno` from `event` common attributes to `call`-only events.
* `message` changed from a map to an array of parameter objects.
* Added `labels`, `client`, and `recorder` to `metadata`.
* Removed `layout`, `layout_owner` and `app_owner` from `metadata`.

## v1.1.0

* `parameters` changed from a map to an array of parameter objects.
* Added `receiver`, a parameter object.
