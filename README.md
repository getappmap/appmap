- [About AppMap](#about-appmap)
- [appmap.json](#appmapjson)
    - [version](#version)
    - [metadata](#metadata)
    - [classMap](#classmap)
      - [Common attributes](#common-attributes)
      - ["package" and "class" attributes](#%22package%22-and-%22class%22-attributes)
      - ["function" attributes](#%22function%22-attributes)
    - [events](#events)
      - [Common attributes](#common-attributes-1)
      - ["call" attributes](#%22call%22-attributes)
      - ["return" attributes](#%22return%22-attributes)
      - ["self", "parameters" and "return_value"](#%22self%22-%22parameters%22-and-%22returnvalue%22)

# About AppMap

This is the home project for AppMap, automatic extraction of metadata from code and visual depiction. 

# appmap.json

The `appmap.json` file contains the metadata which is extracted from a code repo. 

`appmap.json` is a JSON object which is composed of the following elements:

```
{
  "version": <integer>,
  "metadata": {
    "repository": <url>,
    "branch": <string>,
    "commit": <string>,
    "labels": [ <string> ]
  },
  "classMap": [ <list of objects> ],
  "events": [ <list of objects> ]
}
```

* **classMap** Hierarchical information about the packages, classes and functions. Required.
* **events** List of function call events which occurred during code execution. Optional.

### version

*Required* version number to which the file conforms.

The initial version is `1.0`.

### metadata

*Optional* information about the code from which the data was generated. This object describes the code from which the
data was generated. 

* **repository** *Optional* Home URL of the code.
* **branch** *Optional* code branch.
* **commit** *Optional* commit identifier.
* **labels** *Optional* list of arbitrary labels describing the AppMap.

### classMap

*Required* list of code objects. There are three types of supported objects: `package`, `class`, and `function`. 

Note that the terms `package` and `class` are loosely. In general, they refer to language-specific concepts such as
`package`, `class`, `interface`, `module`, etc. Since an AppMap is a fairly high-level representation of the code, the
detailed differences between these language-specific concepts aren't usually very important. Rules of thumb:

* Use `package` to represent a directory organization of code. A package may contain packages and classes, but not functions.
* Use `class` to represent a type declaration in a code file. A class may contain classes and functions, but not packages.

#### Common attributes

Each object has the following attributes:

* **name** *Required* name. Should be the local name of the object, not the fully-scoped name. Example: `User` or
  `show`, not `MyApp::User` or `User#show`.
* **type** *Required* object type. Must be `"package"`, `"class"`, or `"function"`.

#### "package" and "class" attributes

"package" and "class" have the following attributes:

* **children** *Optional* List of child objects which are semantically contained.

#### "function" attributes

Each "function" has the following attributes:

* **location** *Required* File path and line number, separated by a colon. Example: `/Users/alice/src/myapp/lib/myapp/main.rb:5`.
* **static** *Required* flag if the method is class-scoped (static) or instance-scoped. Must be `true` or `false`. Example: `true`.

### events

*Optional* list of events which were recorded during program execution. 

Without the `events` list, an AppMap describes the code of a particular repository. The `events` list details the
sequence of function calls which occurred during actual program execution. 

#### Common attributes

Each event object has the following attributes:

* **id** *Required* unique identifier. Example: 23522.
* **event** *Required* event type. Must be ` "call"` or `"return"`.
* **defined_class** *Required* Name of the class which defines the method. Example: "MyApp::User".
* **method_id** *Required* Name of the function which was called in this event. Example: "show".
* **static** *Required* flag if the method is class-scoped (static) or instance-scoped. Must be `true` or `false`. Example: `true`.
* **path** *Required* path name of the file which triggered the event.  
* **lineno** *Required* line number which triggered the event.
* **thread_id** *Required* identifier of the execution thread.

**Note**

To make it possible to correlate function call events with "function" objects defined in the class map, the `path` and
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
values.

* **object_id** *Required* unique id of the object.
* **class** *Required* fully qualified class name of the object.
* **value** *Required* string describing the object. This is not a strict JSON serialization, but rather a display
  string which is intended for the user. These strings should be trimmed in length to 100 characters.

