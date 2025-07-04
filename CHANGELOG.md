# [1.1.0](https://github.com/opencitations/heritrace/compare/v1.0.0...v1.1.0) (2025-05-29)


### Bug Fixes

* **catalogue:** add support for entity classes with multiple shapes ([44c415f](https://github.com/opencitations/heritrace/commit/44c415f0ed344c99826f625966ffd2e90c02c791))
* **catalogue:** integrate shape consideration in catalogue operations ([3eb7119](https://github.com/opencitations/heritrace/commit/3eb71193658d72e868624cc356f4238e58c2df68))
* **display_rules:** ensure consistent objectShape handling in grouped triples ([9704f68](https://github.com/opencitations/heritrace/commit/9704f68c0fe39913faf0dd3839f782177ecb2093))
* enhance validation and robustness with SPARQLWrapper retry mechanism ([1cb6f1c](https://github.com/opencitations/heritrace/commit/1cb6f1cbb6002e9c6958d5bc912a3204583ba8ce))
* **entity:** add shape support in validation and related components ([87d582e](https://github.com/opencitations/heritrace/commit/87d582e3503c488252d3ce0d0fe4c05da2b33ab5))
* **entity:** enhance human readable predicates and entity handling ([30b8c84](https://github.com/opencitations/heritrace/commit/30b8c84e6beaae98ba7df2da0d971d9d7241ef29))
* **entity:** prevent highest priority class and shape override in deleted entities ([fe9cfef](https://github.com/opencitations/heritrace/commit/fe9cfef616050244df49ba300d1139c994c58d57))
* **entity:** upgrade to Time Agnostic Library 5.0.1 ([f1f7551](https://github.com/opencitations/heritrace/commit/f1f7551ff1121792d0708b68c5bc7b81f7e71120))
* **filters:** handle None shape in human_readable_class filter ([fa33ee6](https://github.com/opencitations/heritrace/commit/fa33ee6e3d3798ab013c45ce0a9d50ed46e78d27))
* handle None case for matching form field in get_grouped_triples ([d6b5477](https://github.com/opencitations/heritrace/commit/d6b54771f54e7815b2672831a3e4cd52a465bab7))
* improve sorting and shape handling in catalog data retrieval ([9b19f5e](https://github.com/opencitations/heritrace/commit/9b19f5e0ebe4ad48318112ea27804b7eba016b2a))
* migrate linked resources to async frontend loading ([3cdef89](https://github.com/opencitations/heritrace/commit/3cdef8944a0c7369b6b1b047d043bdfedcc1e2cc))
* **templates:** improve render_triple consistency for mandatory values ([b1592a9](https://github.com/opencitations/heritrace/commit/b1592a9d2871002e8431c0ac392d3fa659a03f02))
* **templates:** simplify entity type labels in resource displays ([07aa3bd](https://github.com/opencitations/heritrace/commit/07aa3bdced7604c63ad23c89601352b6914466f7))
* **time-vault:** enhance entity filtering with shape support ([0787a67](https://github.com/opencitations/heritrace/commit/0787a67474fa62a73af4e3f6eca7cdc9a76aaa64))
* update about functionality for tuple-based class,shape structure ([3a14790](https://github.com/opencitations/heritrace/commit/3a147906970073d1cfc5d65bfe420411995022ff))


### Features

* add a new filter `human_readable_class` to improve the display of class names in templates ([66f8beb](https://github.com/opencitations/heritrace/commit/66f8beb1dc27859c5e7cedc8f880ca4817bc7efe))
* **entity:** add specialissue shape to part of predicates for journal article ([de242f1](https://github.com/opencitations/heritrace/commit/de242f1e056b1ae4e933ad6d9ad0c21314f90c5c))
* implement shape-based entity triples determination ([ebc2ca9](https://github.com/opencitations/heritrace/commit/ebc2ca90d97c403b4c777db32ffb1106b510093e))
* **merge:** add primary source specification for resource merging ([8d61257](https://github.com/opencitations/heritrace/commit/8d61257043a7aa9e7efb370c64c6601a7d13bc36))

# 1.0.0 (2025-05-14)


### Bug Fixes

* Add cardinality validation to entity edit page ([7979058](https://github.com/opencitations/heritrace/commit/79790589ab6b9273b3553df37d643d02d742d2ef))
* add config.py creation step in GitHub workflow ([7fa0e59](https://github.com/opencitations/heritrace/commit/7fa0e59b57d9ad884a9add36aa09759ab3db584d))
* add ISBN, abstract, keywords and collaborator support to Proceedings and Series ([8ec733e](https://github.com/opencitations/heritrace/commit/8ec733e00bea42d8ca01dbcbe17020143cf66c6c))
* add URI generator enhancements and error handling ([1858ea3](https://github.com/opencitations/heritrace/commit/1858ea36950c30ff94180651081318b07bbb294c))
* Adjust the pagination logic to use a limit+1 strategy for determining if more results are available ([6281829](https://github.com/opencitations/heritrace/commit/6281829897e5d297da3d3d87809780c4bf6ff0a5))
* beautifulsoup4 dependency ([e680f61](https://github.com/opencitations/heritrace/commit/e680f6142ad91af902bdd2209cd6cad3f91ef1ab))
* complete adaptation to tuple-based (class, shape) keys structure ([d3a7404](https://github.com/opencitations/heritrace/commit/d3a7404c43705b929d21de4f33833cd30cab0e81))
* consider inverse types in SHACL validation ([aa460a4](https://github.com/opencitations/heritrace/commit/aa460a4eef3aa2b69e057d23273f3b3343424995))
* correct assertion in unit test for quadstore changes ([309cf78](https://github.com/opencitations/heritrace/commit/309cf780520cfb6f5c92dfc5d69757ce32cd0dd6))
* correct literal datatype handling and update dependencies ([f50d4f1](https://github.com/opencitations/heritrace/commit/f50d4f168b2ae614e7acf98b3d41c80d96c4eaae))
* correct priority class selection logic ([754938d](https://github.com/opencitations/heritrace/commit/754938d523ef3b35a0bad4fa95704dad2e4b6da7))
* **display:** apply shape-based display rules to frbr:partOf for correct labels ([50ee794](https://github.com/opencitations/heritrace/commit/50ee7943bda15600f43bafa7d83b0485d287f95f))
* **editor:** remove automatic value conversion in delete method ([8aa94e6](https://github.com/opencitations/heritrace/commit/8aa94e63b7eac4091cbbd7ea6370cf3751115168))
* enhance resource locking to include linked resources ([52e1766](https://github.com/opencitations/heritrace/commit/52e176645dacc8de2974051850d5f64209283f7b))
* enhance SPARQL utility functions and add integration tests ([3877ea2](https://github.com/opencitations/heritrace/commit/3877ea2afdd732d95a89465b9b791916daee06ef))
* Fix entity search functionality and restore change entity handler ([cc6762b](https://github.com/opencitations/heritrace/commit/cc6762b3db43a29a53e16bf632acab8cbdd467fd))
* Fix graph context handling and refactor parameter normalization in Editor ([1c4f425](https://github.com/opencitations/heritrace/commit/1c4f425d985a3137454dd52f312c6b65e1ceb252))
* Fix ordered property deletion and proxy entity detection ([ec3e4bc](https://github.com/opencitations/heritrace/commit/ec3e4bc6224bc82c27082bbc4dd94e0e1a0f48a8))
* Fix Time Vault pagination discrepancy ([58855e2](https://github.com/opencitations/heritrace/commit/58855e29a12dfd1b77dd9c58b74729842d4000d6))
* For delete operations, we only need to validate cardinality constraints ([2db63b7](https://github.com/opencitations/heritrace/commit/2db63b76e5668417289578b0c746a8d990f9537f))
* Handle deleted entity restoration using provenance data instead of dataset exploration ([8cef99c](https://github.com/opencitations/heritrace/commit/8cef99c70508f020df9d76167b42eb02432a8201))
* implement retry mechanism and search support improvements ([7bc9464](https://github.com/opencitations/heritrace/commit/7bc94646fd6d35c51b4ddbad7a38d879ef10c48c))
* improve backend validation for existing entities ([3da6946](https://github.com/opencitations/heritrace/commit/3da69466cca4a666b3608af25fd1edd66d516a5c))
* improve counter initialization and switch to Redis ([4cf9f02](https://github.com/opencitations/heritrace/commit/4cf9f02456c4e14262bbddc9fb107044d6d7e26f))
* Improve Editor error handling and entity deletion ([d406748](https://github.com/opencitations/heritrace/commit/d40674893014a2f60772905debd7e6fa255cad78))
* improve entity deletion by automatically handling references ([1f8252c](https://github.com/opencitations/heritrace/commit/1f8252ce4e85bc3ba9e9c005162b32e020556e3c))
* improve performance and Docker configuration ([b8ef6e9](https://github.com/opencitations/heritrace/commit/b8ef6e9ddb707bfcac219e703ebf7fb089b99c27))
* improve proxy and orphan handling with separate strategies ([d20b08f](https://github.com/opencitations/heritrace/commit/d20b08ff02e99f8a74d3acfb7a6ff8012ec426f5))
* improve responsive button layout on small screens ([6b442d0](https://github.com/opencitations/heritrace/commit/6b442d0a6cecdb0208ef042675fd0196586d9997))
* improve the handling of snapshot descriptions ([7a8004c](https://github.com/opencitations/heritrace/commit/7a8004cdeff6d0f508928542faef564192039e8f))
* invert priority logic in display rules to use lower values for higher priority ([7edcfd1](https://github.com/opencitations/heritrace/commit/7edcfd1fe144df6bdd0ac74e6b60399cfdbc3567))
* **macros:** update display logic for shape options in dropdown ([29b3197](https://github.com/opencitations/heritrace/commit/29b3197b13aa1f6c8aa2a190fc36a93643a91b48))
* merge reuses rdflib-ocdm ([9f36555](https://github.com/opencitations/heritrace/commit/9f365552cdc942f9a648fa15a3c51776f7926651))
* **merge:** resolve f-string syntax error in find_similar ([2a6ba4f](https://github.com/opencitations/heritrace/commit/2a6ba4f0ca1de6c562dc4255eb69f5ccd0448582))
* optimize orphan check to only run for entity deletions ([dcae6d5](https://github.com/opencitations/heritrace/commit/dcae6d59621ab80844cdb0350a5ff324a375f781))
* optimize performance by utilizing connected resources ([e0adf2a](https://github.com/opencitations/heritrace/commit/e0adf2aa35715afcbf7aba2df1b40fc8c23ecea3))
* Prioritize top-level fetchValueFromQuery for container display ([ff1d02f](https://github.com/opencitations/heritrace/commit/ff1d02f8d68b26e734afa3140dd607ceeee115f8))
* properly encode search terms for Virtuoso text index ([1245979](https://github.com/opencitations/heritrace/commit/1245979e78a831a2099c705ff956330c68668f68))
* Refactor form data collection and enhance entity reference handling ([32f0dc6](https://github.com/opencitations/heritrace/commit/32f0dc604a495157a3cb32868f5f453ca31a5e86))
* Remove SPARQL query escaping to fix search functionality ([e1ef689](https://github.com/opencitations/heritrace/commit/e1ef6893bbddd1e4f37914a1bca741272a89a432))
* replace direct Config references with Flask's current_app.config ([0f75eca](https://github.com/opencitations/heritrace/commit/0f75eca0120994e5e4b1abbbb681a00f9cf7649d))
* resolve entity deletion concurrency issue ([3a0e532](https://github.com/opencitations/heritrace/commit/3a0e532c10c8bc3070d6cca04ee021e3541b2145))
* **shacl_utiils:** update entity keys to use tuples (class, shape) for rule identification ([bac2b15](https://github.com/opencitations/heritrace/commit/bac2b1551fd7cdbbc91029380b9ac2baa4dc9d2d))
* Unify container display for Journal Articles to enhance consistency and prevent bugs ([731c76d](https://github.com/opencitations/heritrace/commit/731c76d6b6733c9ca0813c34d3bbd9e53b4b80b4))
* Update dependencies and refine project definition ([ede4c6f](https://github.com/opencitations/heritrace/commit/ede4c6f02279be5414d8e37edbd5c062f615eeda))
* update display rules for editor and collaborator formatting ([33f8fa1](https://github.com/opencitations/heritrace/commit/33f8fa1391a6f1530fc89498fe0b85c8db5afa45))
* update sorting logic and display rules documentation with shape targeting ([8fe0fb7](https://github.com/opencitations/heritrace/commit/8fe0fb7101107af860003c39516ad8c1e13fa0a9))
* update SPARQL mock path in unit tests for entity types ([bfacfc5](https://github.com/opencitations/heritrace/commit/bfacfc595a04d8d59ae53a1099a765aa4e0bdd22))


### Features

* Add comprehensive tests for merge blueprint and related utilities ([d635c69](https://github.com/opencitations/heritrace/commit/d635c693e752f64294fa73c77afb6af38a2a2f12))
* Add loading indicators and fix URIRef conversion bugs ([b62045a](https://github.com/opencitations/heritrace/commit/b62045aa527d70b7fa0831261318c34bc5c53574))
* add presentation markdown and accompanying speech ([a1699f2](https://github.com/opencitations/heritrace/commit/a1699f2f81a01409cb2ec59e7b34e76cdd008a1c))
* Add primary source URL handling in entity creation ([b30cdf5](https://github.com/opencitations/heritrace/commit/b30cdf56808c62940df1b585ac52beaa8cdd1f6a))
* Add search support to display rules and improve UI ([e84abd7](https://github.com/opencitations/heritrace/commit/e84abd794d307850e6001c0b69d32bb7e135abc2))
* **display_rules:** Enhance similarity properties configuration and logic ([db838b1](https://github.com/opencitations/heritrace/commit/db838b1c0787865aa24379ed491f2aecb2ec9bc9))
* enhance orphan handling with intermediate relation cleanup ([ee097f2](https://github.com/opencitations/heritrace/commit/ee097f2bf6fc7e392e0eafb6025950817420e9bb))
* Enhance search functionality and display rules ([de0c202](https://github.com/opencitations/heritrace/commit/de0c20285728a7addb6b0ba8f1a78c1dde46752a))
* Enhance similar resources functionality with pagination and load more feature ([5ea95f5](https://github.com/opencitations/heritrace/commit/5ea95f55823f05ccb779bec2025a128bf993f7e8))
* **entity_editing:** enable primary source selection during modification ([c32d23e](https://github.com/opencitations/heritrace/commit/c32d23e5340c068c51044a4aa9853fd9035dad6d))
* Implement entity merging functionality and similarity detection ([a754909](https://github.com/opencitations/heritrace/commit/a754909d7e17ddaf7c916f2063808e9b9e977ac5))
* Implement parent entity search for nested fields ([1cfcaea](https://github.com/opencitations/heritrace/commit/1cfcaead330c8d4f0c7eab444cf817e828c61615))
* implement top-level search functionality ([b4842f3](https://github.com/opencitations/heritrace/commit/b4842f347fcffdf9947183761fdce5133690246b))
* Introduce helper functions for entity creation and metadata enrichment ([7a2ac6c](https://github.com/opencitations/heritrace/commit/7a2ac6c518c8639002e03831dddf198e85e8f595))
* **routes:** Integrate linked resources functionality and update API endpoint ([8d083ab](https://github.com/opencitations/heritrace/commit/8d083abbf12a43d2c9b414e17afdb396cdc89ef6))


### BREAKING CHANGES

* Counter storage now requires Redis instead of SQLite.
The MetaCounterHandler class has been completely refactored to use Redis,
and the initialization logic has been moved to the URIGenerator plugin.
