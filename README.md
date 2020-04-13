- [About AppMap](#about-appmap)
- [Usage](#usage)
  - [AppMap client command reference](#appmap-client-command-reference)
  - [Pruning](#pruning)
- [appmap.json](#appmapjson)
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
      - [Function call attributes](#function-call-attributes)
      - [Parameter object format](#parameter-object-format)
      - [Exception object format](#exception-object-format)
      - [Function return attributes](#function-return-attributes)
      - [HTTP server request attributes](#http-server-request-attributes)
      - [HTTP server response attributes](#http-server-response-attributes)
      - [SQL query attributes](#sql-query-attributes)
      - [Message attributes](#message-attributes)
      - [Example](#example-2)
- [Changelog](#changelog)
  - [v1.2](#v12)
  - [v1.1](#v11)

# About AppMap

This is the home project for AppMap, automatic extraction of events and metadata from code. 

# Usage

Basic usage of AppMap proceeds according to the following steps:

1. Install the AppMap client for the programming environment. For example, install the Ruby gem for Ruby
   projects; install the npm package for Node.js; install the Go module for Golang.
2. Run the AppMap client to perform static or dynamic inspection of the code. In static mode, the client inspects all
   the project code without actually running any of it. In dynamic mode, the client executes the program through some
   scenario, and records all the important events (e.g. SQL queries, function calls) which occur. Whether performing static or
   dynamic inspection, the output is an `appmap.json` file.
3. Upload the `appmap.json` file to the AppLand server.

## AppMap client command reference

Each AppMap client performs basically the same functions:

* `appmap inspect` Perform a static inspection of the code and generate `appmap.json`.
* `appmap record` Perform a dynamic inspection of the code by actually executing and observing the code. Generate
  `appmap.json` on completion.
* `appmap upload` Upload an `appmap.json` file(s) to the AppMap server.

## Pruning

When `appmap.json` is uploaded to the AppMap server, the file can be pruned to remove extraneous information.
This results in a more compact and faster upload. For example, if a dynamic inspection was performed, then only the code
which was actually executed at some point during the program execution may be retained.

# appmap.json

The file `appmap.json` contains metadata which is extracted from a code repo.  It is a JSON object with the following
general structure:

```
{
  "version": <integer>,
  "metadata": <object>,
  "classMap": [ <tree of package, class, and function objects> ],
  "events": [ <list of event objects> ]
}
```

### version

*Required* version number to which the file conforms.

See the [Changelog](#changelog) section for version history.

### metadata

*Optional* information about the code from which the AppMap was extracted.

Metadata has the following attributes:

* **name** *Optional* scenario name.
* **repository** *Optional* home URL of the code.
* **labels** *Optional* list of arbitrary labels describing the AppMap.
* **app** *Optional* name of the app to assign to the Scenario.
* **feature** *Optional* name of the feature to associate with the Scenario. If the named feature does not exist, it may
  be created.
* **feature_group** *Optional* name of the feature group to associate with the Scenario. If the named feature group does not exist, it may
  be created.
* **language** *Optional* information about the programming language in which code is written.
  * **name** *Required* name of the programming language
  * **engine** *Optional* name of the programming langugae engine, e.g. VM variant.
  * **version** *Required* programming language version
* **frameworks** *Optional* list of frameworks which the code uses.
  * **name** *Required* name of the framework.
  * **version** *Required* version of the framework.
* **client** *Required* information about the AppMap client which recorded the scenario.
  * **name** *Required* short name of the client.
  * **url** *Required* unique URL of the client.
  * **version** *Optional* version of the client.
* **recorder** *Required* information about the method which was used by the client to record the scenario.
  * **name** *Required* name of the recording method. This name must be unique to the client, but need not be unique across different clients.
* **recording** *Optional* information about the entry-point function which was recorded.
  * **defined_class** *Required* name of the class which defines the entry-point function.
  * **method_id** *Required* name of the recorded function.
* **git** *Optional* information about the state of the Git repo.
  * **branch** *Required* code branch.
  * **commit** *Required* commit identifier.
  * **status** *Required* status of the repo relative to the commit, represented as a list of status messages. If the repo is clean, the status should be an empty list.
  * **tag** *Optional* latest tag.
  * **annotated_tag** *Optional* latest annotated tag.
  * **commits_since_tag** *Optional* number of commits since the last tag.
  * **commits_since_annotated_tag** *Optional* number of commits since the last annotated tag.

#### Example

```
{
  "name": "Identity management in the UI permits login with a local password",
  "repository": "https://github.com/applandinc/appmap",
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

* **location** *Required* File path and line number, separated by a colon. Example: "/Users/alice/src/myapp/lib/myapp/main.rb:5".
* **static** *Required* flag if the method is class-scoped (static) or instance-scoped. Must be `true` or `false`. Example: true.

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
* **defined_class** *Required* name of the class which defines the method. Example: "MyApp::User".
* **method_id** *Required* name of the function which was called in this event. Example: "show".
* **static** *Required* flag if the method is class-scoped (static) or instance-scoped. Must be `true` or `false`. Example: true.
* **path** *Required* path name of the file which triggered the event. Example: "/src/architecture/lib/appland/local/client.rb".
* **lineno** *Required* line number which triggered the event. Example: 5.
* **thread_id** *Required* identifier of the execution thread. Example: 70340688724000.

**Note**

In order to correlate function call events with function objects defined in the class map, the `path` and
`lineno` attributes of each "call" event should exactly match the `location` attribute of the corresponding function.

#### Function call attributes

Each "call" event has the following attributes:

* **receiver** *Required* parameter object describing the object on which the function is called. Corresponds to the `receiver`, `self` and `this` concept found in various programming languages.
* **parameters** *Required* array of parameter objects describing the function call parameters.

#### Parameter object format

Each parameter is an object containing the following attributes:

* **name** *Required* name of the parameter. Example: "login".
* **object_id** *Required* unique id of the object. Example: 70340693307040
* **class** *Required* fully qualified class name of the object. Example: "MyApp::User".
* **value** *Required* string describing the object. This is not a strict JSON serialization, but rather a display
  string which is intended for the user. These strings should be trimmed in length to 100 characters. Example: "MyApp
  user 'alice'"

#### Exception object format
* **class** *Required* fully qualified class name of the exception. Example: "com.myorg.InvalidUserException"
* **message** *Required* description of the exception cause. Example: "User attribute not defined: 'email'"
* **object_id** *Required* unique id of the object. Example: 70340693307040
* **path** *Optional* path name of the file where the exception was thrown. Example: "/src/main/java/com/myorg/models/User.java".
* **lineno** *Optional* line number where the exception was thrown. Example: 264.

#### Function return attributes

Each "return" event has the following attributes:

* **parent_id** *Required* id of the "call" event corresponding to this "return".
* **return_value** *Optional* object describing the return value. If present, this value uses [parameter object format](#parameter-object-format).
* **elapsed** *Optional* elapsed time in seconds of this function call.
* **exceptions** *Optional* array of exceptions causing this method to exit. If present, this value uses [exception object format](#exception-object-format). When an exception is a wrapper for an underlying `cause`, the cause is the next exception in the `exceptions` array.

#### HTTP server request attributes

A "call" event which represents an HTTP server request will have an `http_server_request` attribute, which is an
object with the following elements:

* **request_method** *Required* HTTP request method. Example: "POST".
* **path_info** *Required* HTTP request path. Example: "/users".
* **protocol** *Optional* HTTP protocol and version. Example: "HTTP/1.1", "http://".

See: HTTP Request-Line https://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html

#### HTTP server response attributes

A "return" event which represents an HTTP server response will have an `http_server_response` attribute, which is an
object with the following elements:

* **status** *Required* HTTP [status code](https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html)

#### SQL query attributes

A "call" event which represents a SQL query will have an `sql_query` attribute, which is an
object with the following elements:

* **database_type** *Required* name of the database. Example: "postgresql".
* **sql** *Required* SQL query string.
* **explain_sql** *Optional* query plan provided by the database engine.
* **server_version** *Optional* database server version.

#### Message attributes

A "call" event which represents the receipt of a message will have a `message` attribute, which
is a list of objects in [parameter object format](#parameter-object-format).

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
    "self": {
      "class": "Module",
      "value": "AppLand::Local::Client",
      "object_id": 70340693307040
    },
    "parameters": {
      "name": {
        "class": "String",
        "value": "ruby",
        "object_id": 70340689027780
      }
    }
  },
  {
    "id": 2,
    "event": "return",
    "defined_class": "AppLand::Local::Client",
    "method_id": "install",
    "path": "/src/architecture/lib/appland/local/client.rb",
    "lineno": 7,
    "static": true,
    "thread_id": 70340688724000,
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
    "self": {
      "class": "AppLand::Local::UI::UI",
      "value": "#<struct AppLand::Local::UI::UI visualizations=nil>",
      "object_id": 70340689072680
    },
    "parameters": {
      "visualizations": {
        "class": "Array",
        "value": "[AppLand::Local::UI::Component::Timeline, AppLand::Local::UI::Component::CallStack, AppLand::Local::",
        "object_id": 70340693502240
      }
    }
  },
  {
    "id": 4,
    "event": "return",
    "defined_class": "AppLand::Local::UI::UI",
    "method_id": "initialize",
    "path": "/src/architecture/lib/appland/local/ui.rb",
    "lineno": 41,
    "static": false,
    "thread_id": 70340688724000,
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
    "self": {
      "class": "Module",
      "value": "AppLand::Local::Client",
      "object_id": 70340693307040
    },
    "parameters": {}
  },
  {
    "id": 6,
    "event": "return",
    "defined_class": "AppLand::Local::Client",
    "method_id": "client",
    "path": "/src/architecture/lib/appland/local/client.rb",
    "lineno": 11,
    "static": true,
    "thread_id": 70340688724000,
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

# Changelog

## v1.2

* `message` changed from a map to an array of parameter objects.
* Added `labels`, `client`, and `recorder` to `metadata`.
* Removed `layout`, `layout_owner` and `app_owner` from `metadata`.

## v1.1

* `parameters` changed from a map to an array of parameter objects.
* Added `receiver`, a parameter object.
