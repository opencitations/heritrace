# Configurator 3t transcription

## Warm-up exploration

Allora, ora sto registrando. La prima fase, quella esplorativa. Ok, quindi qua ho le categorie della mia collezione. Ok, quindi ho un journal, 100 journal article. Lo posso ordinare in questo caso: titolo e data di pubblicazione. Ok, 15 issue, 5 volume, 100 manifestation. Ok, ok.

Identificativo, il titolo, l'autore. Ok. Se faccio edit. Ok, posso aggiungere un identificativo, aggiungere l'autore, modificare la data. Va bene.

Ok, ora se io vado su un nuovo record. Tipo.. Aspetta. Questo no, questo è un blog. Aspetta. In questo caso mi sa che non hanno creato un'entità. No, non c'è. Ok, publication date. Un minuto. Io posso anche aggiungere il journal direttamente da qua. Il Journal è Quantitative Science Studies. L'identifier... In questo caso l'ISSN. 

Ok, ok, Time Machine, Snapchat 1. E se adesso la modifico ovviamente mi creerà uno Snapchat nuovo. Se io vado alla versione. No, l'ho messo, lo mette ok in automatico, figo. Qua non posso aggiungere identificativi, non posso aggiungere l'ORCID. Dipende dalla configurazione di SHACL sicuramente. Ora qua ho due journal, ok.

## Task 1: Add SHACL validation for abstract

Ok, ora invece passo al task numero uno, che un attimo devo ritrovare. Ok, era qui. Questo qua.

Allora, innanzitutto capiamo come dobbiamo usare SHACL. Allora, c'è la cartella config, c'è SHACL. Allora, c'è journal article, journal article, journal article, journal article shape.

Sarà un sh:property per forza. La metterò, non credo conti l'ordine però mettiamolo sotto titolo. Ok, penso che così va bene.

Devo modificare anche l'interfaccia. L'interfaccia la modifico. Dove era? Qua, YAML.

Sarà sempre in config. Dobbiamo andare su journal article, display name, journal article, ok. Display properties, credo.

Title. Ok, penso che vada bene. Ecco, abstract, ok.

Però qua come faccio a vedere? Perché lì appunto ho aggiunto un campo che è necessario. Quindi, se faccio un nuovo record, ok. L'unica cosa è, forse sarebbe utile avere un modo per capire quali risorse sono incomplete a seconda dello schema SHACL che voglio utilizzare.

Adesso ho modificato lo schema SHACL, quindi chiaramente ho aggiunto una nuova proprietà, quindi le risorse che già erano presenti risultano incomplete perché non hanno quella proprietà. Quindi questa cosa andrebbe forse segnalata in qualche modo. Magari c'è già il modo, ma io non lo trovo.

Ok, interrompo.

## Task 2: Add abstract display support

Ora faccio il passo al task numero due. Configure display rules for the... ok. With this requirement. In parte l'ho già fatto, credo, però ok, vediamo. Appropriate for long form text.

Sicuramente modificare questo. Display rules configuration. Quindi andiamo un attimo alla documentazione.

Display rules. Ok, mi sa che l'avevo già fatto perché ho già messo textarea. Se non sbaglio, eh.

Se non sbaglio l'avevo già fatto. No, scusa, volevo vedere il file YAML.

Abstract, l'ho messo tutto title. Textarea. Lì ci siamo, secondo me.

Sì. Ok, quindi questa registrazione è un po' inutile, scusa.
