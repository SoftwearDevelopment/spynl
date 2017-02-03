Routing
================================

Spynl takes control over many aspects of routing.

URLDispatch
----------------
(no traversal) default routes /{resource}/{method} /{method}


Endpoint registration
-----------------------
`config.add_endpoint`

It's custom (do not use Pyramid's `config.add_view`) - why? (at least to have a grip on documentation of endpoints, TODO: look for other reasons)


Custom resource registration
-------------------------------
`config.add_resource`

A resource class at least needs a `paths` attribute, can also have `available_in_production`.

Multiple paths (aliases) is possible in Spynl.


Custom routes
---------------
Basically adding meta data and a function to `spynl.resource_routes_info`. TODO:
show tutorial, argue why it is better to do it this way than simple using
Pyramid's `config.add_route` directly. Hint: It has to do with applying routes
to resources unknown in the current plugin. It has/had a use case but maybe everyone
is better off now without it. Research.
