# HERITRACE in Action: The ParaText Project as a Case Study for Semantic Data Management in Classical Philology

# Abstract

* Brief overview of HERITRACE as a semantic data editor for cultural heritage institutions  
* Introduction to ParaText as a significant implementation case study  
* Summary of key findings and contributions  
* Highlighting the benefits for domain experts in classical philology

# 1\. Introduction

* Overview of challenges in digital management of classical philology resources

In the digitisation era, scholars who want to start a research in classical philology have to conduct a bibliographic cross-research querying mainly two different types of databases, the bibliographical repertoires and databases to find resources and the online public access library catalogues (OPAC) to localize resources.

These two instruments, only apparently independent of one another, share some features which are today crucial for the bibliographic research and which enhance the formal cataloguing. The online library catalogue inherits the features of the traditional print library catalogue and contains formal bibliographic metadata related to the publication (*e.g.*, title, author, publication date) together with location and inventory number, but also permits to conduct thematic research through the Dewey Decimal System, subjects and keywords; on the other hand, even though a bibliographical database also includes the same features of the online library catalogue – except for data relating to the location of the resource which are replaced by the link for online open access publications – it has as its main objective a thematic research as in-depth as possible and its main challenge in the semantic data management.

The exactitude in the selection of the keywords, the management of the correct hierarchy in the subject tree, the accuracy of the thematic classification, the rigorous balancing between brevity and completeness in the abstracts, that constitute the process of the semantic cataloguing which implies the editor’s critical approach, have an immediate impact on the correctness of the results and on the efficacy of the bibliographic research by the users.

The semantic data management involves the creators and developers of a bibliographical database, even before the editors, and played a pivotal role also in the ideation and development of *ParaText* bibliographical database.

* Introduction to the ParaText project and its objectives

The *ParaText* project is an excellent case study to analyze the dynamics, opportunities and critical issues of humanistic computing and in general of digital representations in the peculiar field of Greek philology and in particular in the study of ancient exegesis of Greek poetic texts of the Archaic, Classical and Hellenistic ages.

The *ParaText* project aims: (a) to carry out an in-depth investigation on the relationship between literary text and exegetical paratext in the manuscript transmission of ancient Greek poetry; (b) to develop, and make available to the community of scholars, a prototype tool of hypertextual transcription that allows to describe, understand and further explore this cultural phenomenon; and (c) to enhance the book heritage of a renowned Italian library by a public exhibition of important medieval manuscript witnesses of ancient Greek poetry and related exegesis.

The *ParaText* team brings together scholars expert in text and transmission of ancient Greek poetry and related exegesis from Antiquity to the Byzantine era, with the purpose of achieving new goals in the field in terms of both method and knowledge. The study of ancient scholarship concerning poetic works which were at the core of Greek civilisation – archaic epic and lyric, Attic theatre, Hellenistic poetry – enables us to draw a diachronic and a synchronic map of exegetical strategies and a description of their typological and functional features. We dedicate particular attention to the logical and structural organisation of the exegetical paratexts: linear commentary (*e.g. hypomnemata*, continuous commentaries); ‘hypertext’ commentary (*e.g. scholia*, *lexica*). We also explore the relations between the two types of products, i.e. motives, dynamics and effects of transforming an arrangement as linear source into a hypertextual one and vice versa. The results are (or will be) published in articles on academic journals, in books and in a final conference with its proceedings. These publications are destined to scholars and advanced students specialized in the field, as well as to scholars who may be interested in the issue from an interdisciplinary perspective.

The research also aims to design an innovative standard for textual analysis, by producing the prototype of a hypertextual tool enabling scholars to represent and explain the relationship between literary text and exegetical paratext in ancient books. This prototype consists of a *Repertoire of Hypertext Transcriptions* (RHT) of case studies, each of them provided with introductory information, Italian and English translation, commentary and bibliography. It is accompanied by a *Lexicon of Ancient Greek Exegesis* and a critical *Bibliographical Database* on the topic, which is the core of our collaboration with *OpenCitations* (see Peroni and Shotton 2020). The *Repertoire* and all its complements are published online as open access tools, available to scholars, advanced university students and non-specialist cultivated people interested in the knowledge and understanding of literature and book heritage.

Some of the most significant manuscripts being studied belong to the *Veneranda Biblioteca Ambrosiana* in Milan. They are the core of a public, virtual exhibition (hosted in the website of the project), destined to scholars, students and educated people.

* The need for semantic data management in classical philology

As the birth of the *ParaText* project points out, a flourishing of studies on ancient Greek exegesis has marked the last decades of research in classical philology and has required new instruments and technologies to respond the scholars’ needs of systematise and share the results they achieved.

In this perspective, the *ParaText* bibliographical database plays a complementary role to the *Année Philologique*, the most complete and specialised bibliographical database relating to all aspects of ancient Greek and Roman civilizations, and indeed their comparison sheds light on the value of semantic data in the bibliographic research in the field of classical philology and on their potential and limits, especially those referring, on the one hand, to the possibility that thematic classification, subjects and keywords offer to make the bibliographic resources searchable and to conduct the research at different levels of detail and, on the other hand, to the difficulty in selecting information and specialist terminology which correspond to users’ knowledge and guide the search towards the expected results.

Compared to the *Année Philologique* database, the *ParaText* bibliographical database permits to count on the specialised language related to ancient Greek exegesis and search criteria customised and specific for this branch of classical philology studies, but it has to face the same challenges in the management of semantic data.

* The role of HERITRACE in addressing these challenges  
* Scope and structure of the paper

# 2\. Related Work

* Overview of existing digital initiatives in classical studies (e.g., Année Philologique)  
* Specific challenges in classical philology data management  
* Current approaches and limitations

# 

# 

# 3\. HERITRACE Implementation in ParaText

## 3.1 System Architecture and Configuration

* Customization of HERITRACE for ParaText requirements  
* SHACL shapes and YAML configurations specific to classical philology resources  
* Integration with existing data sources

## 3.2 User Interface for Classical Philology Experts

* Catalog interface adaptations for ParaText  
* Entity creation and editing workflows  
* Search and disambiguation features for classical texts

## 3.3 Provenance Management for Bibliographic Data

* Tracking changes in classical philology metadata  
* Managing contested attributions and interpretations  
* Time Machine implementation for ParaText resources

# 4\. Discussion

## 4.1 Benefits and Challenges

* Advantages of HERITRACE for classical philology data management  
* Challenges encountered during implementation

As *Année Philologique* and *ParaText* project demonstrate, classical philology requires highly specialised databases capable to manage formal and semantic data at different levels, with immediate consequences on the efficiency of research results.

With respect to formal data, one of the challenges encountered during implementation was searching for a correspondence as accurate as possible between the wide range of bibliographic records typologies covered by publications in classical studies and the typologies, with their adaptations, offered by HERITRACE. Analysing a couple of particularly significant cases, the first one relates with ‘Monograph’ typology, which in *ParaText* database refers to monographs *stricto sensu*, but includes also other resource typologies proper to classical studies, i.e. edition, edition with translation and translation, respectively designating critical editions of classical texts, critical editions of classical texts accompanied by a modern language translation, and modern language translations of classical texts not accompanied by Greek or Latin texts. A similar case is that of ‘Miscellany’ typology, which in *ParaText* database includes all types of publications that collect articles written by one or more authors, and that in classical studies are generally distinguished into miscellany *stricto sensu*, that is collective work on various topics, collected essays which relate to collective work on a single topic, and *Festschriften* containing collected articles published in honour of a scholar. Instead, proceedings are common to different field of studies and they did not need adaptation, thus they have in *ParaText* database a proper typology named ‘Proceedings’, together with ‘Proceedings Paper’ typology, both allowing editors to create specific bibliographic records both for the volume and for each article published in the volume.

HERITRACE has given a valid answer to the necessity to detail Monograph and Miscellany typologies, providing the new field ‘Description’ to better specify the typology of the resource entered, and all data that can’t find its placement in other fields (*e.g.*, series, place of publication, edition number). A new challenge might be to define a fixed sequence in the succession of data into the visualisation interface, as well as to manage the correct placement of these formal data during a potential import process.

With regard to semantic data, keywords require special treatment for the description and search function they have in *ParaText* database, a property that places them halfway between keywords *stricto sensu* and subjects. Moreover, they force to face challenges that involve both scholars and editors and therefore content and technical issues. First, the highly specialised vocabulary inherent to a continuously evolving branch of classical philology, as that of the studies on ancient exegesis, implies on one hand the difficulty to select terms commonly accepted by most of the scholars and on the other the need for a flexible management of this semantic data. To give a practical example, ‘exegetical activities’, that is one of the most used keywords, might require a change in ‘exegetical activities and cultures’ in the light of recent discussion among scholars, and manually editing each bibliographic record containing this keyword would mean taking time away from the entry of new records.

A second content and technical issue relating to keywords refers to their typologies, i.e. subject, author, work, genre, manuscript and papyrus, which help to categorise keywords and make them properly searchable. This type of categorisation tries to respond to research needs in classical philology, and particularly to the necessity of conducting research according to different and various criteria. To give once again a practical example, the keyword ‘author\>Homerus’ allows scholars who enter the keyword ‘Homerus’ in the field ‘Ancient authors and texts’ to find all the bibliographic records relating to Homer, on the bases of the proper correspondences between the web editor and the database search mask.

* Lessons learned from the ParaText deployment

## 4.2 Future Directions

* Planned enhancements for ParaText

In the early stages of the project, HERITRACE well answered to the requirements of *ParaText* and in some cases, as has been demonstrated so far, made it possible to gain functionalities not yet available on other similar databases, thus improving bibliographic search in the field of classical philology. Nevertheless, enhancements have been already planned, which partly tend to shape the new database according to the criteria familiar to philologists upgrading its usability, partly permit to offset the gap between the initial objectives and the results that have been achieved thanks to HERITRACE, in the hope that the two projects can grow hand in hand and improve each other.

Three implementations are currently in progress. The first one concerns the possibility of creating links between bibliographic records, and it involves two different types of citations: the first permits to link the bibliographic record of ‘Review’ or ‘Review Article’ typology with the resource they discuss, the second permits to create links between every other kind of bibliographic record typology responding to the need of connecting resources when one is another edition of, a continuation of, a translation of, replies to another resource already entered into the database. The other two implementations, i.e. the database search mask and the visualization interface that allow users to query the database and view bibliographic records, only partially involve HERITRACE but are an indirect test both for HERITRACE and *ParaText* projects, since the findability and the acquisition of the records, together with the cohesion and coherence of data in the visualization interface, depend on the exactitude of the entered data and the interoperability between systems. Moreover, related to the new implementations are the possibility of saving and exporting records and the modalities of these processes, that are crucial to correspond to the philologists’ habits and needs of conducting research.

Due to the similarities with the *Année Philologique* database, some of the planned enhancements take into account the perspective of the evolution of the current interdialogue between the two databases into a future interoperability, which could make it easier to achieve the goal of an updated and complete bibliography on ancient Greek exegesis and, on the contrary, consolidate the complementary role of ParaText bibliographical database to the *Année Philologique* through a mutual data importation, given the chance the former offers to count on collaborative and open access redaction and on bibliographic records compiled within a short time after the resource publication. With this objective, *Année Philologique* and *ParaText* databases have similar structure and entries to ensure the correspondence between the fields of the two systems.

One of the main obstacles to the achievement of this goal relates to copyright, since *ParaText* bibliographical database would publish for free contents that *Année Philologique* database makes accessible by subscription. On the other hand, only formal data could be effectively involved in this process without any kind of editorial check, except for a rapid supervision; in fact semantic data would require a critical revision by the editors and an adaptation to the criteria and perspectives specific of each database, and even if abstracts could be quite easily adapted, subjects of *Année Philologique* and keywords of *ParaText* are mostly different.

Another aspect that could be considered in order to improve usability and data entry into *ParaText* database and assimilate it to the layout the philologists are used to is the disposition of the fields within the web editor interface. To give a couple of examples from the current organisation of the fields, the ‘Page’ field is almost at the end of the fields list even if its content would justify its placement immediately after the ‘Description’ field; moreover, the ‘Translator’ field is separated from ‘Author’, ‘Editor’ and ‘Collaborator’ fields since it is immediately preceded by the ‘Publisher’ field. Grouping separately formal and semantic data and using more consistency in the succession of the fields could help to better reorganise the current layout along the lines of resources referencing to bibliographic record, which already have an appropriate section at the end of each bibliographic record frame.

With reference to semantic data, the fundamental role played by keywords in the accuracy of description and search of the resources makes quite urgent the need for a system that, once again taking advantage of the interoperability between web editor and search mask, allows both editors and users to have an overview of the keywords already entered in the database and to select them or enter new ones according to needs. This requirement arises from the necessity to use keywords since the beginning, without having at our disposal subject headings but having, at the same time, the necessity of a controlled vocabulary. These circumstances led to create a file containing all the keywords with their hierarchic organisation, that needs to be translated into a supplement technology for the *ParaText* bibliographical database. The iter would probably require the passage through an intermediate phase with a dropdown menu, before arriving at the ultimate objective, that is the creation of a *Thesaurus*, which could also interact with the *Lexicon* of *ParaText* project.

The last planned enhancement in response to the original objectives of *ParaText* project pertains to the collaborative nature of the *ParaText* bibliographical database, which allows all scholars to enter data and create bibliographic records behind access to the web editor via password. This requires management and monitoring of the process that will be articulated into two phases: a first phase during which scholars can create records that will be verified and checked by an administrator, and a second phase without administrator but supported by the possibility HERITRACE offers both to track the responsible agents and primary data sources and to constantly emendate bibliographic records (see Massari and Peroni 2025). In this perspective, the monitoring during the first phase might require more attention from the administrator since, at this stage, the web editor does not provide an area in which storing bibliographic records during the intermediate phase between the entering of the record and its validation. The only functionality that the administrator can rely on is the Sort by dropdown menu that allows users to order items by date of creation, with the inconvenience for the administrator of having to remember which is the last validated item for each type of bibliographic record.

* Potential applications in other classical studies projects  
* Integration with broader digital humanities initiatives

# 5\. Conclusion

* Summary of HERITRACE's contribution to ParaText  
* Broader implications for semantic data management in classical studies  
* Future research and development opportunities

# Acknowledgements

# References