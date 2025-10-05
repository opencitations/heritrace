# Configurator 5t transcription

## Warm-up exploration

Ok, so... ah vabbè, per fortuna li teniamo. Ho appena aperto HERITRACE, quindi la prima cosa che vedo è Go to the Catalogue qui, e qui mi manda il catalogo, quindi ecco il menu di navigazione è cambiato, ha selezionato il catalogo, new records, direi che è appunto aggiungere un nuovo record, time vault, ok, lo dice anche access and restore deleted entities, quindi fa quello insomma, fa vedere appunto le entità che sono state cancellate e fa il restore, perché mi immagino che ci sarà un modo per fare il restore, ok.

Quindi lui mi dice che c'è un journal attualmente, ed è questo International Journal of Fruit Science, con questo omid qui, quindi omid è questo omid identificativo, journal articles, quindi questi sono articoli presenti dentro il catalogo, journal issues, quindi dà soltanto il link ovviamente alla issue, journal volume e la manifestation, ok, quindi sono vari file di manifestation.

Ok, quindi questi sono i link che appunto se clicco, ah ok, io pensavo che appunto era il link a proprio l'entità in nome di OpenCitation, invece l'apre in HERITRACE, e quindi per esempio questa cos'era? Era una manifestation che ho cliccato, quindi type manifestation, starting page, ending page, resource, referencing this e questa qui per esempio, e se faccio così, view entity, direi che mi porta all'entità, ok.

Resource, similar resources, ok, publication date, quindi questi sono i metadati che ci sono dentro Meta, identificativi e quant'altro, qui posso fare l'edit e la delete del resource. Visit, immagino nel suo sito originale, ah no, visit, faccio così, ah quindi tutti e due portano alla stessa cosa direi, ok.

Quindi non posso però risalire alla cosa originale, alla Openalex o a DOI a questo punto, e questo sempre HERITRACE, quindi tutti i link a questo punto mi sembra che portino a HERITRACE stesso, non ci sono dei link esterni. Ok, vediamo che cos'è, fa vedere che cos'è questo, expression, va bene, fa vedere il journal stesso, identifier, ah eccoli, resources, referencing this, e quindi sono part of questo, part of quello per esempio, part of questo. Ok, journal volume, immagino che questi sono tutti i journal volume, va bene, quindi diciamo che posso navigare tra i vari elementi del catalogo, quindi a parte journal, journal article, tutti gli altri hanno l'url qui. w3id.org, che però apre qui dentro, non va ovviamente a OpenCitations.

## Task 1: Add SHACL validation for abstract

Adesso passo al primo task. Quindi dovrò andare nel file di configurazione immagino di SHACL qua e metterci Abstract. Allora io direi che quindi devo andare a vedere SHACL e questo è giù nell'article è tipo una property e quindi se faccio copy di questo così e lui mi dice quindi è opzionale praticamente ok va bene allora facciamo come ho fatto a fare questo già? Avevo già messo create, ah avevo già fatto reload ok quindi questo adesso c'è l'abstract posso fare anche il delete ah non c'è la stellina quindi ok questo era il task va bene.

## Task 2: Add abstract display support

Ok, passo al task 2 Add abstract display support Add abstract... Ah, perché? Ah, adesso non volevamo metterlo tipo title, forse Ok Input type appropriate for long-term text Think aloud, va bene. Ah ok, quindi questo punto non è shacl.ttl ma direi che è questo. Ok, aperto qui Rules Display name, journal article Ok, che è quindi quello che stiamo facendo noi. Display properties, quindi queste sono le sue proprietà Infatti c'è il type, c'è identifier. Vediamo se c'è title, c'è title. Ah, eccolo, tipo title e textarea. Che è quindi questo.

Quindi io faccio una copia di questo. dcterms:abstract. Display abstract. Should be displayed sì textarea sì Support search Non so cosa sia, ma metto false Anzi ancora Minimum SHACL search, quindi search questo prima Search target, lascio solo questo Vediamo se c'è Faccio così, create.

Adesso non è più caricata, perché? Ah, è staccato docker. Si è staccato docker Containers New record, abstract Ah, eccola Ok, ho solo riavviato docker, ma comunque adesso va E l'ha messo, ah l'ha messo sotto title In realtà nel task mi chiedeva di fare una roba del genere forse anche Vedi c'è proprio display name, input type Properties should appear under the title in the display order Quindi adesso appear in effetti under title Ma perché? Ah, perché fisicamente credo che stia proprio under title Quindi non è che devo metterci l'order come proprietà Quindi va bene Ok, direi che questo task è completato.
