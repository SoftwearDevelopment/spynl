Features
===============

* Session handling
* (HTML) Email support
* Content Type Negotiation
* Custom (De)serialization
* I18N support
* Plugin management
* Error handling (views, logging, sending erros to aggregator services)
* JSON schema validation
* Plugins can add ...
 *- routes
 *- view derivers
 *- required ini settings
 *- (de)serialisation handlers for data types
 *- pre- and post install hooks (e.g. for system libraries installation or cleanup)
* CI support
 *- Jenkinsfile and build task
 *- Dockerfile and build script
 *- deployment script to build on a ECR
* about endpoints for introspection
 *- endpoint swagger docs
 *- build information
 *- plugin versions
 *- pip environment
 *- ini settings
