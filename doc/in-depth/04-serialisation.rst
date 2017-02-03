==============
Serialisation
==============

JSON is default choice

methods of selecting a different type: Content-Type Header, file extension, ...

supported types: XML, CSV, HTML, YAML

Incoming HTTP data is decoded and outgoing data encoded. Special data type (de)serialisations are easy to add,
useful e.g. for DateTime objects.
