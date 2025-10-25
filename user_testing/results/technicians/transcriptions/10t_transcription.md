# Configurator 10t transcription

## Warm-up exploration

Hello, I will be testing HERITRACE. I apologize if I sound a bit sick, that's because I am. Also, I apologize if I'm not following certain formalities. I'm not really a very formal person. At any rate, let us begin with the testing session of HERITRACE. So, I am testing it as a technician, as a configurator, because of my background.

So, let's start exploring HERITRACE. The landing page has a cute little animation. Let's go to the catalog.

So, in the catalog we have different categories of items, of objects: journals and journal articles, journal issues, volumes and manifestations. I imagine that the manifestations are the references to the embodiments that are the journal articles. Okay, so we can have different pages of objects, items per page: 200, 500.

Okay, I imagine that on a production environment the number of items in each category will be huge. Okay, I can select 500, but it's fine, it's not a negative thing in my eyes, if the number of manifestations or journal articles will be so high that displaying them all on the same page is impractical.

Okay, we can sort the categories alphabetically. Okay, so there is a new record, so actually let's create those records. So, let's create maybe a journal first.

DOI 10.1.1234/sample, title: example journal. Okay, so please provide the URL, the primary source for this entity or leave blank if not applicable. There is a current default that is this test dataset for user testing that I'm using, so I'm leaving it as is, even though it says leave blank.

Okay, entity created successfully. Example journal, so now let's create a journal article. So, DOI 10.1.431/example, title: example journal article.

Author: I will use myself as a responsible agent. I will click those no results found buttons that appear in the list. Okay, just one author and date, let's do today.

Okay, and for the journal I have used 10.1.1234, example journal. Okay, it's linking it nicely. I will add this as a new record.

If I edit this, example journal article 2.0, save changes, confirm, success. Let's visit the Time Vault, it's empty because there is nothing deleted yet. So, let's try to find my example journal article.

Okay, so this is just a personal thing. It may not be a problem considering the target users of the software, but considering I am looking for a journal article and I'm sorting by the title, the items are sorted by the title, it's correct, but the names, the titles of the articles do not appear at the front.

I imagine this is normal, but for me as a new user, this is a bit weird. It was example, example. Okay, so it's at the end.

Okay, I don't think that's correct, that's fully correct, it shouldn't be at the end. Okay, if I go to the Time Vault, there's snapshot 1 where I created this, snapshot 2 where I changed the title name. Okay, let's go back to this and delete it.

Yes, I will delete this and also the journal. And we have those two items in the Time Vault. Okay, we can sort them by the deletion time or by title, ascending or descending, same limits for items per page.

We can restore them, which I won't do, but there are last valid versions. Okay, this has the modification to the title, that is correct. Okay, so I don't really have any other reflections about the webpage, maybe.

Okay, I see that you have used Bootstrap, especially for the content of the page, and that's fine. Okay, the problem that I personally have with Bootstrap, it may not be applicable to you, but I often dislike how when you put something in the containers in Bootstrap, they are very, very narrow. So, as you can probably see here, I use a 1440p screen, so the content of the page is tiny, takes a quarter of the width probably.

I know that you can probably work around it, because it's honestly a me problem probably, but at any rate you could probably also define the widths of the containers yourself for larger screen sizes somewhere in the CSS files. But in general, I like it. I would like actually, I would like to see a dark mode.

Right, so this warm-up exploration actually lasted for much longer than I expected, but let's move on to the configuration tasks. So, I have already opened the files for editing. So, actually I will restore both the journal and the journal article, so we can then look at the functionality that I'm supposed to add inside of those objects.

## Task 1: Add SHACL validation for abstract

So, right, let's start with adding the SHACL validation for abstracts. So, I have here shacl.ttl, which is the set of icons that contains the SHACL information for the shape of the objects. So, we are interested in adding abstracts to journal articles using this dcterms property, and what I need to do is I have to extend the SHACL shape.

So, this is the shape for Fabio journal article, so this is what we are interested in. So, I am unsure if we need... if there is a preference where I need to put the new property. I imagine not, or rather I assume that there is none, and I will put it at the end.

So, sh:property, sh:property, squared brackets, I'm going to finish with a dot as it was before, sh:path, and we are interested in dcterms:abstract, semicolon, sh:, so we are interested in text. If we look at the other properties, we can see that we can use... sh:node uses different shapes, from what I can understand, because we have a schema shape, which has the rdf:type of node shape, so if we wanted to use this new property as a new shape of its own, new object type, we would use sh:node, but we don't.

So, we could define it as... let's call it multiple datatypes, as here, with the case of publication date, with sh:or, the publication date can accept dates, year, months and years, as sh:datatype, and, however, we are interested only in the textual representation, so I will use the same as the title here: sh:datatype xsd:string. I believe that this is the only basic XSD type that exists solely for the purpose of textual representation. What we are also interested in is adding a limit to the number of abstracts, so if either an article doesn't have an abstract, so a min count of 0, or it has an abstract, therefore the max count is 1. Apologies for the noise in the background, if there is any, there is a thunderstorm.

Right, so, considering this Turtle file did work before, as you can see on the left side of the video, I assume there is nothing wrong with using a semicolon instead of a colon when describing properties, so I will save it, and reload. Call to reload the HERITRACE window. Very well, if I edit it, I can add the abstract at the end of this article. For now, I will not edit it further, we will move on to the second task, which is adding the display support for it, or maybe, okay, I will perhaps just copy the Lorem Ipsum text, just in case. Yes, I will leave it as is. Okay, so, as you can see, now, we specified, well, we added the abstract, the dcterms abstract as a property. However, it doesn't have a label, and by default, I would say, it doesn't cut off in a full sense, but the display cuts off, it's scalable horizontally, you can see the entirety of it.

## Task 2: Add abstract display support

So, let's move to display rules, and for this one, I will, what I will do is start as simple as possible. There is, for example, this huge SPARQL query for fetching URI displays, which I will probably have to edit, in order to, actually, no, I actually don't need to do that, considering I edited the resource, and the abstract is displaying itself, there should be no need to, there should be no need to actually edit it, which is interesting. In that case, why would we need the SPARQL query?

So, starting with the property. This is a dcterm, so it has per-orb dcterms:abstract, with display name of abstract, which should be enough for the first subtask of this task, adding the property display name of abstract. Okay, it also moved the abstract under the title, which actually does fulfill subtask number three, which is supposed to show abstract under the title, so this means that the order of display of properties of each object depends on how they are listed in the display properties.

And we are interested in defining an input type that is appropriate for long-form text. Okay, so how do we find it? So, if we see all the display rules, and actually we can just search for input type, there are two in the entire file, both of them input type textarea. Okay, and if we look at any other journal article, you can see that the title, even if it's longer than the width that is available for this input type, it does create new lines, which is what we are interested in. So, this means we have to just add input type textarea, and after reloading, we fulfilled the second to the last subtask: appropriate for long-form text.

There is one more thing that I'm interested in. Okay, so we do have this scrollable box containing text now for abstract, which is great. And what I'm actually interested in is: this isn't really that applicable, I think, but it may happen that we have very, very long words.

I'm honestly unsure on whether or not very long words are organic in English, like they are, for example, in German, but let's say I put a very long string without any spaces, just characters, like A, right? So I want to save it, and what I'm wondering is: will this long string of characters result in new line breakages? So will it display just in the same way that it's displayed right now in this editing text box that we can see? No. Okay. So, we can make the browser window larger, and yeah, okay, so once again, like the only actual problematic thing that I can think of right now is the potential usage of very long, very long protein names.

Like if you have a journal article that will have in its abstract a full name of a protein, which shouldn't happen, but it could hypothetically, then you would have the same result as here. Okay. Okay.

So, that is the end of the task. Okay, so to finish up, I'm going to do the questionnaires and the written reflections. I will also record this just in case.

## SUS questionnaire completion

Okay. So, I think that I would like to use this system frequently. Yes, but I will put a strong disagree here because of two things.

One is that if I go look at the layout of the testing package, if I go to the database, I can see that the database is hosted in OpenLink Virtuoso, and any application that provides me with an interface to interact with whatever's in Virtuoso is a positive thing. And the second thing, I actually do like XML files because, it's a long story, but this is basically XML files, editing XML files for video games was how I started my journey to becoming a technical person. So, I can read, I can write XML files, like related markup languages pretty quickly.

What I hate about editing those files by hand with more complex examples is actually something HERITRACE does very well, and that is linking between existing objects. So, normally in an XML file or a TTL file, you would have to manually specify the links between objects, between object 1 and 2, in object 1 and 2, etc. Here you add the link in one of the objects and it is done for you.

So, I found the system unnecessarily complex, strongly disagree. I don't think that there is anything complex about how the application is laid out for the end user. However, the system was easy to use, strongly agree. I would need the support of a technical person to be able to use this system. I am a technical person, I will put strongly disagree here. I assume that this question is, would I need the support of another technical person in this specific case.

I found that various functions in the system were well integrated. In general, yes. In general, yes.

There were minor hiccups, but in general, yes. I will put agree. It is whether to put agree or strongly agree.

Okay, let's assume that it is solely about functionality. Okay, solely about functionality, 5. I do strongly agree. Maybe too much inconsistency, not really, you know.

I would center some buttons vertically, maybe. If you want to go for a look like that, maybe. Maybe it is something I would do.

But honestly, I am not a designer, I am not a frontend person, so you probably shouldn't be listening to my design, my thoughts about design in general. I would imagine that most people learned to use this system very quickly. Yes, I really don't see any complications about using HERITRACE.

This is actually a good question, since I have to extend the system. Okay. Yes, so I did mention this when I opened this perseus.yaml, that I did expect that I would have to extend this massive SPARQL query to get abstract, but it doesn't seem to be the case.

So I can't see it automatically, like where does the abstract come from then, because it doesn't seem to be this query. And there's nothing else for a journal article, at least, that makes me directly interact with this SPARQL at the end, at the endpoint. So, okay, would learn to use this system quickly.

Yes, if they just went with their heart. If they started overthinking like me, I would put 4. I found this system very cumbersome to use, I would disagree. As I said, it's pretty straightforward, same with the confidence.

I needed to learn a lot of things before I could get going. No, I didn't need to learn anything, actually. Okay, written responses.

## Written reflection

Did you know SHACL before taking this test? No. I was, I am aware of TTL, I am aware of subject, predicate, object triples, etc. But SHACL, no.

This was the first time I've ever heard of it. Did you know HERITRACE before taking this test? I will cross no, I've never used it. I've heard of it before taking this test, but only by hearing about it in the past month, as something Arcangelo was working on.

I never knew what HERITRACE is about, basically. But I had never used it. This was the first time.

How effectively did HERITRACE support you in these configuration tasks? Okay, this is an interesting question in the sense that the configuration tasks were adding validation, SHACL validation for abstract and adding abstract display support. So, you did see what I interacted with in the system, in HERITRACE. So, I did add abstract, right, to SHACL, to the SHACL shape, shacl.ttl. And this abstract did appear in the editing section.

I added the constraint, so the abstract is optional. And yeah, there was one box, right, okay, yeah. So, this article doesn't have an abstract.

If I go to edit resource, I can add an abstract. If I don't add it, then it's fine. Okay, so it works fine.

It supported me in a sense that I could actually, I can see the changes that I've made in the shacl.ttl file, in the display, upon saving and reloading. So, not live, but almost live changes.

What I could also do is, also try to, I could have, I could have intentionally done this task incorrectly, to see what would happen. The error message is how easy it would be to work out that something is not okay. But, considering the task only asked me to do specific tasks, as the end user would do them, I did not do that.

Yeah, so I could see these almost live changes, and be able to act upon them. So, I could add the abstract almost, basically immediately after saving the shacl.ttl file and reloading the browser window, and act upon them on reloading the browser window.

Okay. Now, what were the most useful features that helped you accomplish your work? Again, just as I said before, the editing, edit resource, part of, let's say the object subpage, the object page probably. Since it's here where the object actually appears, where it changed place, when I changed the display rules.

The main weaknesses or frustrations you encountered. As I've mentioned before, there was this, if you have a long word inside of the textarea, there is no new line until the word ends. That's it, basically.

What additional features would make this task easier? I don't think there's any, actually. In the sense that, when I edited shacl.ttl, when I edited display rules, when I saved those files, I could instantly reload the page and see the results of my changes. So, I can't really think of any.

And I believe this concludes my testing as a technician of Arcangelo's HERITRACE. Again, I'm sorry if I sound a bit sick.
