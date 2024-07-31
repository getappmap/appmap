# Data Specification for AppMap Sequence Traces

## Overview
This specification describes the AppMap Sequence Trace format, which is a JSON structure representing a trace of application events, including HTTP server requests, router operations, and external service calls. This format is optimized for usage in constructing sequence diagrams.

AppMap sequence traces typically use the file extension `.sequence.json`.

## Root Structure
The root object contains two main properties:
- `actors`: An array of [actor objects](#actors)
- `rootActions`: An array of [action objects](#action-object) representing the top-level actions

### Actors
An actor is a distinct part of the application that executes code or serves as a point of ingress or egress. It could be a software component, a service, or even a conceptual entity within the application architecture. Actors represent the "who" in the system, the actions (represented by the action objects) show the "what" - the specific operations or events occurring between actors.

Examples of actors include, but are not limited to:
- HTTP server requests
- External service calls
- Databases
- Software packages
- Classes

Each actor object in the `actors` array has the following properties: 
- `id`: String, unique identifier for the actor
- `name`: String, human-readable name of the actor
- `order`: Number, used for sorting actors in sequence, indicative of how these actors operate within the system.

### Root Actions
The `rootActions` array contains action objects that represent the top-level operations in the trace.

## Action Object
An action object represents a specific operation or event that occurs within the traced application. It's the core component of the trace structure, providing detailed information about the system's behavior and interactions. Each action object captures a discrete step in the application's execution, such as a function call, an HTTP request, or an external service interaction. It serves to document the flow of operations, their hierarchical relationships, and performance metrics.

Action objects are the core of the trace structure. They are nested to represent a hierarchy of operations.

### Common Properties
All action objects have the following common properties:
- `nodeType`: Number, indicates the type of action node
- `digest`: String, a hash or unique identifier for the action
- `subtreeDigest`: String, a hash or identifier for the entire subtree of this action
- `children`: Array of child action objects (optional)
- `elapsed`: Number, execution time of the action in seconds
- `eventIds`: Array of numeric event idenifiers, referring to the events within the associated AppMap event array

### Action Types
Different `nodeType` values correspond to different action types:

#### Type 6 (Query)
This action type represents database queries or similar data retrieval operations.

Additional properties:
- `caller`: String, actor identifier of the calling module
- `callee`: String, actor identifier of the database or query executor
- `query`: String, the SQL query being executed
- `digest`: String, a hash of the query or `'truncatedQuery'` if the query was truncated
- `subtreeDigest`: String, always `'undefined'` for query actions
- `children`: Array, always empty for query actions
- `elapsed`: Number, execution time of the query in seconds
- `eventIds`: Array of numbers, containing the event ID of the query event

#### Type 5 (External Service Call)
This action type represents interactions with external services or APIs, including details about the request and response.

Additional properties:
- `callee`: String, actor identifier of the called service
- `route`: String, HTTP method and URL of the external call
- `status`: Number, HTTP status code of the response

#### Type 4 (HTTP Server Request)
This action type represents incoming HTTP requests to the application, capturing details about the route and response status.

Additional properties:
- `callee`: String, actor identifier of the HTTP server receiving the request
- `route`: String, HTTP method and route of the request
- `status`: Number, HTTP status code of the response

#### Type 3 (Function Call)
This action type represents internal function calls within the application, providing details about the caller, callee, and function characteristics.

Additional properties:
- `caller`: String, actor identifier of the calling module
- `callee`: String, actor identifier of the called module
- `name`: String, name of the called function
- `static`: Boolean, indicates if the function is static
- `stableProperties`: Object containing hashable properties:
  - `event_type`: String, always `'function'`
  - `id`: String, name of the function
  - `raises_exception`: Boolean, indicates if the event had raised an exception
- `returnValue`: Object describing the return value:
  - `returnValueType`: Object with `name` property indicating the type
  - `raisesException`: Boolean, indicates if the event had raised an exception

#### Type 2 (Conditional)
This action type is currently not used.

#### Type 1 (Loop)
This action type represents repeated operations or iterations within the application.

Additional properties:
- `count`: Number, number of iterations
- `children`: Array of action objects that are repeated

## Constraints and Validations
- All `id` fields should be unique within their context
- `elapsed` times should be positive numbers
- `status` codes should be valid HTTP status codes
