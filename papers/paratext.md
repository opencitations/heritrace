# HERITRACE in Action: The ParaText Project as a Case Study for Semantic Data Management in Classical Philology

## Abstract

HERITRACE is a semantic data editor designed for cultural heritage institutions, addressing the gap between complex semantic web technologies and domain expert needs. The ParaText project, a specialized bibliographical database for ancient Greek exegesis at the University of Bologna, demonstrates HERITRACE's capabilities in classical philology. This paper examines how HERITRACE enables non-technical scholars to manage complex semantic data through SHACL-based form generation and validation, while ensuring comprehensive provenance tracking and change management via the OpenCitations Data Model adaptation.

## Introduction

In classical philology, scholars face a fundamental challenge: managing complex bibliographic data that requires both domain expertise and technical precision. Semantic data - structured information represented using Resource Description Framework (RDF) standards that enables machines to understand relationships between concepts - offers powerful solutions for representing scholarly knowledge, but its technical complexity has traditionally excluded humanities experts from direct data curation.

The ParaText project at the University of Bologna exemplifies this challenge. ParaText aims to investigate relationships between literary texts and exegetical paratexts in manuscript transmission of ancient Greek poetry, develop hypertextual transcription tools for scholars, and enhance Italian library heritage through public exhibitions of medieval manuscripts. The project produces a Repertoire of Hypertext Transcriptions, a Lexicon of Ancient Greek Exegesis, and a critical Bibliographical Database - all requiring sophisticated semantic data management beyond traditional database approaches.

Classical philology presents unique requirements for semantic data management. Scholars work with highly specialized terminology, contested interpretations that evolve through scholarly discourse, and complex relationships between texts, commentaries, and manuscript traditions. Traditional database systems cannot adequately represent these nuanced relationships, while existing semantic web tools require technical expertise that most humanities scholars lack.

HERITRACE bridges this gap by providing a user-friendly semantic data editor that conceals RDF complexity while preserving semantic integrity. The system enables domain experts to create, edit, and maintain semantically valid datasets with comprehensive provenance tracking, focusing on data curation rather than technical implementation.

## The Domain Challenge 

Classical philology's semantic data requirements become evident through comparison between specialized and generalist databases. The Année Philologique, founded by Jules Marouzeau in 1926, serves as the primary bibliographical reference for classical studies with over 900,000 records. However, its generalist approach cannot capture the nuanced distinctions required for specialized research in ancient Greek exegesis.

The subject 'Scholia, commentaries' in Année Philologique encompasses 521 bibliographic records representing a broad category insufficient for detailed scholarly investigation. ParaText employs far more specific terminology: while both databases use 'scholia', ParaText distinguishes it from 'hypomnema' (commentary) and provides granular classifications including 'D-scholia', 'VMK-scholia', 'scholia exegetica', 'h-scholia', and 'Ge-scholia' for different Homeric scholia classes. Additional distinctions include temporal categories like 'scholia vetera' for ancient scholia and typological specifications such as 'short scholia', 'frame-scholia', and 'scholia à recueil' indicating length and manuscript positioning.

Among ParaText's approximately 400 records pertaining to ancient Greek poetic text exegesis, 179 employ the 'scholia' keyword. Considering that among Année Philologique's 521 'Scholia, commentaries' records, only few pertain to ancient Greek poetry, many resources remain hidden from potentially interested scholars. This demonstrates that specialized terminological precision enables research depth impossible through generalist approaches.

ParaText organizes this complexity through four hierarchical macro-categories: 'exegetical cultures and activities', 'exegetical products', 'exegetical signs and layout', and 'ancient tradition'. Each macro-category contains specialized terms, and when any term is entered as a keyword, the corresponding macro-category must also be included, enabling research at both general and detailed levels while maintaining controlled vocabulary standards.

The scholarly tradition of questioning transmitted texts directly influences bibliographical databases in classical philology. This critical approach manifests in specialized record types like 'Review Article' alongside standard 'Review' categories, and 'in response to' link types highlighting scholarly debates. However, semantic data face the most scrutiny as they result from critical editorial decisions that directly impact research effectiveness.

## The Technical Gap

Traditional approaches to semantic data management create significant barriers for humanities scholars. RDF requires understanding complex ontologies, SPARQL query languages, and graph-based data structures - technical concepts foreign to most classical philology researchers. Existing semantic web tools like Protégé focus on ontology development rather than content creation, while platforms like Wikidata provide limited customization for specialized domains.

Furthermore, classical philology requires sophisticated provenance tracking - the ability to record who made what changes when and why. Scholarly assertions must be traceable to their sources, and competing interpretations must coexist within the same dataset. Traditional database systems cannot adequately represent these temporal and evidential relationships, while semantic web solutions typically require custom development for each use case.

The challenge extends beyond individual scholars to institutional requirements. Cultural heritage institutions need systems that non-technical staff can operate while maintaining data quality and institutional standards. They require seamless integration with existing workflows, comprehensive audit trails for scholarly accountability, and export capabilities for data sharing and preservation.

Existing semantic content management systems fragment these requirements across multiple platforms. Semantic MediaWiki requires external plugins for change tracking, while ResearchSpace lacks built-in versioning mechanisms. This fragmentation increases cognitive overhead and creates data consistency risks, particularly problematic for scholarly applications where accuracy and accountability are paramount.

## HERITRACE Solution

HERITRACE addresses these challenges through a comprehensive semantic data management platform designed specifically for cultural heritage applications. The system employs SHACL (Shapes Constraint Language) - a W3C standard for validating RDF data - to automatically generate user interfaces and validate semantic consistency without requiring users to understand underlying RDF structures.

SHACL defines constraints and validation rules for semantic data models, specifying which properties entities can have, their data types, and relationships between entities. HERITRACE interprets these SHACL definitions to automatically generate appropriate form interfaces: text fields for literal values, dropdown menus for controlled vocabularies, and relationship selectors for linked entities. This approach ensures that users work within semantically valid boundaries while using familiar form-based interfaces.

For ParaText, HERITRACE implements an adaptation of the OpenCitations Data Model (OCDM), a comprehensive ontological framework designed for bibliographic metadata representation in scholarly contexts. OCDM extends established semantic web vocabularies including FABIO for publication types, DATACITE for identifier management, and FRBR for hierarchical relationships between bibliographic entities. This adaptation enables sophisticated representation of classical philology resources while maintaining compatibility with broader scholarly infrastructure.

The system's provenance model addresses scholarly requirements for comprehensive change tracking and accountability. Each entity modification generates timestamped records capturing essential metadata: temporal information indicating when changes occurred, agent information linking modifications to authenticated users through ORCID integration, and source documentation connecting changes to evidential basis. This provenance tracking operates transparently, requiring no additional effort from users while ensuring complete audit trails.

HERITRACE implements change management through snapshot-based versioning, storing complete entity states at each modification point. This approach enables scholars to examine historical versions, compare changes over time, and restore previous states when necessary. Unlike delta-based systems that store only differences, snapshot storage ensures data integrity and simplifies temporal navigation for non-technical users.

The system integrates authentication through ORCID (Open Researcher and Contributor ID), ensuring that all changes are attributed to verified scholarly identities. This integration supports institutional accountability requirements while enabling collaboration across organizations.

## Results and Impact

ParaText implementation using HERITRACE demonstrates significant advantages over existing approaches to bibliographic data management in specialized humanities contexts. The system successfully enables non-technical scholars to create and maintain sophisticated semantic datasets while preserving the interpretive flexibility essential for humanities research.

The case study of Chiara Martis's 2013 article "L'enigma del PLouvre inv. 7733 verso: l'epigramma dell'ostrica" illustrates how semantic precision impacts research effectiveness. Comparison of abstracts across three sources reveals editorial challenges in terminology selection. The journal describes "explanatory commentary," Année Philologique acknowledges an "elegy or epigram" debate, while ParaText initially used "commented edition" - the most precise term identifying the exegetical product as text-plus-paratext unity rather than paratext alone.

However, ParaText's initial choice to use only 'epigram' as a keyword concealed ongoing scholarly debate and limited discoverability for researchers studying elegiac commentary. This necessitated scholarly discussion, ultimately leading to abstract revision and introduction of the 'elegy' keyword to maintain research accessibility while preserving interpretive debate - demonstrating how well-designed semantic systems can enhance rather than constrain scholarly discourse.

HERITRACE's integrated workflow approach provides substantial improvements over fragmented solutions. Unlike systems requiring external change tracking plugins or lacking restoration mechanisms, HERITRACE seamlessly integrates correction, documentation, and versioning within unified interfaces. This integration reduces cognitive overhead while ensuring comprehensive audit trails essential for scholarly accountability.

The system's accommodation of contested interpretations proves particularly valuable for humanities applications where multiple valid perspectives may coexist and evolve through scholarly discourse. ParaText editors can modify semantic classifications and abstracts as research progresses, while maintaining complete historical records of changes and their justifications.

## Conclusion

HERITRACE demonstrates that semantic data management can support specialized humanities scholarship while preserving scholarly rigor and accessibility for non-technical users. The ParaText implementation provides evidence that carefully designed semantic systems can accommodate sophisticated classical philology requirements including contested interpretations, evolving terminology, and complex bibliographic relationships.

However, the ParaText project reveals significant limitations arising from interdisciplinary collaboration without preliminary data model coordination. The project emerged from collaboration between distinct research teams - expert in text and transmission of ancient Greek poetry and related exegesis from Antiquity to the Byzantine from the Department of Classical Philology and italian Studies at the University of Bologna, and computer scientists from OpenCitations - each pursuing independent objectives. This distributed approach, while valuable for maintaining disciplinary autonomy, precluded essential preliminary phases of data model definition tailored to classical philology requirements.

Consequently, ParaText adapted the existing OpenCitations Data Model, originally designed for bibliographic metadata of scientific publications, rather than developing a purpose-built ontology for classical studies. While OCDM provides robust foundations for scholarly metadata, its scientific publication focus cannot fully capture the sophisticated semantic requirements of classical philology, particularly the nuanced distinctions between different types of exegetical paratexts, manuscript transmission complexities, and specialized terminological hierarchies that characterize ancient Greek scholarship.

Although HERITRACE functions as a domain-agnostic platform capable of accommodating any data model, future developments should prioritize collaborative data model design phases that integrate domain expertise from project inception, ensuring semantic frameworks adequately represent specialized scholarly requirements rather than requiring post-hoc adaptations of existing ontologies designed for different domains.