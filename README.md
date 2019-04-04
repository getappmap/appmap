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
      - ["package" and "class" attributes](#%22package%22-and-%22class%22-attributes)
      - ["function" attributes](#%22function%22-attributes)
      - [Example](#example-1)
    - [events](#events)
      - [Common attributes](#common-attributes-1)
      - ["call" attributes](#%22call%22-attributes)
      - ["return" attributes](#%22return%22-attributes)
      - ["self", "parameters" and "return_value"](#%22self%22-%22parameters%22-and-%22returnvalue%22)
      - [Example](#example-2)

# About AppMap

This is the home project for AppMap, automatic extraction of metadata from code and visual depiction. 

# Usage

Basic usage of AppMap proceeds according to the following steps:

1. Install the AppMap client for the programming environment. For example, install the Ruby gem for Ruby
   projects; install the npm package for Node.js; install the Go module for Golang.
2. Run the AppMap client to perform static or dynamic inspection of the code. In static mode, the client inspects all
   the project code without actually running any of it. In dynamic mode, the client executes the program through some
   scenario, and records all the important interactions (e.g. function calls) which occur. Whether performing static or
   dynamic inspection, the output is an [appmap.json](#appmap.json) file.
3. Upload the `appmap.json` file to the AppMap server, which creates visual depictions of the code.

## AppMap client command reference

Each AppMap client performs basically the same functions:

* `appmap inspect` Perform a static inspection of the code and generate `appmap.json`.
* `appmap record` Perform a dynamic inspection of the code by actually executing and observing the code. Generate
  `appmap.json` on completion.
* `appmap upload` Upload an `appmap.json` file to the AppMap server.

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
  "classMap": [ <list of objects> ],
  "events": [ <list of objects> ]
}
```

### version

*Required* version number to which the file conforms.

The initial version is `1.0`.

### metadata

*Optional* information about the code from which the AppMap was extracted.

Metadata has the following attributes:

* **repository** *Optional* home URL of the code.
* **branch** *Optional* code branch.
* **commit** *Optional* commit identifier.
* **labels** *Optional* list of arbitrary labels describing the AppMap.
* **username** *Optional* name of the user who generated the AppMap.

#### Example

```
{
  "repository": "https://github.com/applandinc/appmap",
  "branch": "master",
  "commit": "c3424f9",
  "labels": [ "documentation" ],
  "username: "alice"
}
```

### classMap

*Required* list of code objects. There are three types of supported objects: `package`, `class`, and `function`. 

Note that the terms `package` and `class` are used loosely. In general, they encopass language-specific concepts such as
`directory`, `package`, `class`, `interface`, `module`, etc. Since an AppMap is a high-level representation of code, the
detailed differences between these language-specific concepts aren't usually very important. Rules of thumb:

* Use `package` to represent the organization of code into directories. A package may contain packages and classes, but not functions.
* Use `class` to represent a type declaration in a code file. A class may contain classes and functions, but not packages.

#### Common attributes

Each classMap object has the following attributes:

* **name** *Required* name. Should be the local name of the object, not the fully-scoped name. Example: `User` or
  `show`, not `MyApp::User` or `User#show`.
* **type** *Required* object type. Must be `"package"`, `"class"`, or `"function"`.

#### "package" and "class" attributes

Each "package" and "class" has the following attributes:

* **children** *Optional* List of child objects which are semantically contained.

#### "function" attributes

Each "function" has the following attributes:

* **location** *Required* File path and line number, separated by a colon. Example: `/Users/alice/src/myapp/lib/myapp/main.rb:5`.
* **static** *Required* flag if the method is class-scoped (static) or instance-scoped. Must be `true` or `false`. Example: `true`.

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
* **event** *Required* event type. Must be ` "call"` or `"return"`.
* **defined_class** *Required* name of the class which defines the method. Example: "MyApp::User".
* **method_id** *Required* name of the function which was called in this event. Example: "show".
* **static** *Required* flag if the method is class-scoped (static) or instance-scoped. Must be `true` or `false`. Example: `true`.
* **path** *Required* path name of the file which triggered the event. Example: "/src/architecture/lib/appland/local/client.rb".
* **lineno** *Required* line number which triggered the event. Example: 5.
* **thread_id** *Required* identifier of the execution thread. Example: 70340688724000.

**Note**

In order to correlate function call events with function objects defined in the class map, the `path` and
`lineno` attributes of each "call" event should exactly match the `location` attribute of the corresponding function.

#### "call" attributes

Each "call" event has the following attributes:

* **self** *Optional* object describing the instance on which the method is called.
* **parameters** *Optional* object describing the function call parameters.

#### "return" attributes

Each "return" event has the following attributes:

* **parent_id** *Required* id of the "call" event corresponding to this "return".
* **return_value** *Optional* object describing the return value.
* **elapsed** *Optional* elapsed time in seconds of this function call.

#### "self", "parameters" and "return_value"

A common format is used to describe the instance on which a function is called, function parameters, and return
values. These attributes are:

* **object_id** *Required* unique id of the object. Example: 70340693307040
* **class** *Required* fully qualified class name of the object. Example: "MyApp::User".
* **value** *Required* string describing the object. This is not a strict JSON serialization, but rather a display
  string which is intended for the user. These strings should be trimmed in length to 100 characters. Example: "MyApp
  user 'alice'"

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
    "return_value": {
      "class": "Class",
      "value": "AppLand::Local::Client::Ruby",
      "object_id": 70340693343340
    },
    "parent_id": 5,
    "elapsed": 2.0e-06
  }
]
```
