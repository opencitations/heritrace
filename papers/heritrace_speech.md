# HERITRACE: A User-Friendly Semantic Data Editor for Cultural Heritage Institutions
## Presentation Speech

Good morning everyone. Thank you for being here today. I'm Arcangelo Massari from the University of Bologna, and I'm delighted to present HERITRACE - a tool we've developed to bridge the gap between complex semantic technologies and domain expertise in cultural heritage institutions.

## The Challenge

Cultural heritage institutions worldwide face a significant challenge. On one hand, the digitization of collections has opened unprecedented opportunities for preservation, access, and discovery. On the other hand, it has created a technical barrier that many domain experts struggle to overcome.

Consider the curator at a museum with decades of expertise in Renaissance art. They understand the historical context, artistic techniques, and cultural significance of each artifact. However, when it comes to managing the digital representation of these artifacts in semantic formats like RDF, they often find themselves dependent on technical staff.

This creates a bottleneck in the curation workflow. The semantic nature of technologies like RDF, while powerful for machine-readable interoperability, can be intimidating for those without technical expertise. Yet, human interpretation and curation remain essential, as algorithms cannot replace the nuanced understanding of cultural context.

We've observed this tension in projects like the FICLIT Digital Library and OpenCitations at the University of Bologna. Despite their different approaches to semantic technologies, both face challenges in empowering domain experts to directly engage with and curate data.

## The HERITRACE Solution

HERITRACE, which stands for Heritage Enhanced Repository Interface for Tracing, Research, Archival Curation, and Engagement, addresses this gap through five primary objectives:

First, it provides a user-friendly interface for domain experts, allowing them to interact with semantic data without needing technical knowledge.

Second, it implements comprehensive provenance management to document who made changes, when they were made, and what sources informed those changes.

Third, it delivers robust change-tracking capabilities, allowing users to view previous states of the data and restore them if needed.

Fourth, it offers flexible customization options through standardized languages rather than proprietary solutions, making it adaptable to different institutional needs.

Finally, it facilitates seamless integration with existing RDF data collections, eliminating the need for complex data transformations.

Let me walk you through how these objectives translate into practical features.

## User Interface and Functionality

The HERITRACE interface is designed with simplicity in mind, while preserving the full power of semantic data management.

When users first access the system, they see a catalog view organized by categories. Each category represents a type of entity in the collection - articles, journals, artifacts, or any other custom type defined by the institution. Users can easily navigate between categories, sort items, and adjust the display settings to suit their needs.

When selecting an item from the catalog, users access a detailed view that displays all metadata fields in an intuitive format. Each field is clearly labeled and paired with its current value. Editing is seamless - users can modify text directly, add new fields, or remove existing ones. The system provides real-time validation to ensure data consistency and prevent errors.

One of the most powerful features is the disambiguation system. As users type in fields like author names or titles, HERITRACE automatically searches for similar entries to prevent duplication. For example, if someone is adding Franco Montanari as an author, the system will suggest existing entries matching that name, maintaining consistency across the dataset.

## Time Machine and Provenance

Perhaps the most innovative aspect of HERITRACE is its approach to change management and provenance tracking.

The "Time Machine" feature provides a complete timeline for each entity in the database. Every modification generates a new snapshot with detailed provenance metadata - when the change occurred, who made it, what primary source informed it, and exactly what was modified.

Users can explore this timeline, compare different versions, and restore previous states with a single click. This ensures transparency and accountability throughout the curation process while providing a safety net for experimentation.

For deleted entities, we've created the "Time Vault" - essentially a recycle bin that preserves access to removed resources. Items deleted from the main catalog remain accessible through this interface, with metadata about when and why they were deleted. This ensures that no information is ever permanently lost.

## Customization and Integration

While HERITRACE works effectively out of the box, we recognize that different institutions have unique requirements. Our customization approach uses standard technologies rather than proprietary solutions.

Administrators can define data models and validation rules using SHACL - a W3C standard for validating RDF data structures. This allows for precise control over what properties are available for each entity type, their cardinality constraints, and validation patterns.

For visual customization, we use YAML configuration files. These control how entities are displayed, what labels are used for properties, and how the disambiguation system behaves. Custom SPARQL queries can be embedded to transform complex data relationships into user-friendly displays.

Importantly, HERITRACE does not impose a specific ontology or data model. It adapts to the institution's existing semantic structure, making it compatible with various domain-specific standards.

## Real-World Applications

HERITRACE is not just a theoretical solution - it's already being applied in real-world contexts. 

The ParaText project at the University of Bologna uses HERITRACE to manage bibliographic metadata for textual resources. All the examples you've seen in this presentation come from this implementation.

We're also planning integration with OpenCitations - an open infrastructure for disseminating bibliographic and citation data. This will provide an opportunity to test HERITRACE with large-scale, dynamic datasets.

## Future Directions

Looking ahead, we have several key development priorities.

First, we're working on integrating the RDF Mapping Language (RML) to enhance compatibility with non-RDF data formats. This will allow HERITRACE to seamlessly connect with tabular data, JSON, XML, and relational databases, further breaking down technical barriers.

Second, we're planning comprehensive usability testing with 15-20 GLAM professionals. This will combine task-based testing using think-aloud protocols with quantitative measurements to systematically improve the interface.

Finally, we aim to expand HERITRACE adoption within the broader GLAM community. As an open-source project, we welcome contributions and collaborations to enhance the system's capabilities.

## Conclusion

In summary, HERITRACE represents a practical solution to a significant challenge in the digital humanities and cultural heritage fields. By making semantic data accessible to domain experts while preserving its integrity, we enable more efficient and accurate curation workflows.

The system's integrated approach to provenance management and change tracking ensures transparency and accountability, while its flexible customization options allow adaptation to diverse institutional needs.

I invite you all to explore HERITRACE further. The system is available on GitHub and Software Heritage, with comprehensive documentation for both users and administrators. We've also published a research paper with additional technical details, currently under peer review.

Thank you for your attention. I'd be happy to answer any questions and discuss potential collaborations. 