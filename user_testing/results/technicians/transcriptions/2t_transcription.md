# Configurator 2t transcription

## Warm-up exploration

Ok, allora, nei due minuti di warm-up devo capire l'interfaccia, identificare il current configuration state e distinguere tra fully configured entities e quelle che hanno bisogno di additional work. C'è un preloaded dataset di Open Citations.

Ok, allora, catalogo, new record e time vault. Access and restore, ok, quindi qui accedo a cosa c'è già esistente, qui creo un nuovo record e qui modifico, torno indietro. Insomma, posso fare login ma ho capito che sono già autenticata: welcome, you've been automatically logged in to the demo. Nel catalogo già journal, journal article, issue, volume, manifestation, ok. Sort by title, posso ordinare in ordine crescente e decrescente, immagino, cioè quindi alfabetico. Items per page, International Journal of Fruit Science. Perché c'è solo un journal? Se invece clicco su journal article li posso ordinare per titolo, publication date, interessante, ok, decidere quanti visualizzarne per pagina e così via. Journal article quindi, soil and plant response, journal issue.

Il goal di questa sessione è, ok, quindi se io per dire clicco su International Journal of Fruit Science so la tipologia, che identifier ha, il titolo e le risorse che puntano a questo journal che non ci sono. Risorse simili. Se vado in un journal article, ad esempio clicchiamo sul primo: type, identifier, titolo, author, publication date. Ad esempio non c'è l'abstract, non c'è l'editor, ad esempio se si può mettere. Non punta, non punta a nessun journal. No, esatto, perché abbiamo autore, anno, titolo, basta. Ad esempio questo non punta a un journal.

Passati due minuti e mezzo direi che stoppo e vado al configuration task. Direi che, a vedere così, log out, non ho visitato new record ma va bene. Qui posso visitare, ok, questi link.

## Task 1: Add SHACL validation for abstract

Add SHACL validation for abstract, ok, eccoci. Allora, 22 minuti. Va bene, azzeriamo il cronometro perché sto tenendo più o meno giusto per non perdermi nei task che sto facendo, per capire se ci metto molto meno o troppo.

Nell'articolo deve essere possibile aggiungere l'abstract, cosa che al momento non c'è. Non è che non c'era, non si poteva proprio aggiungere. E al massimo one abstract per articolo, quindi vuol dire che può anche non esserci, quindi opzionale. Your task is to modify the SHACL shape to include, ok, queste cose che abbiamo detto. The constraint will allow a maximum of one abstract and a minimum of zero, the abstract is optional. Continue thinking aloud about your process and any difficulties you encounter when working with SHACL constraints. Note on hot reloading: after modifying configuration files, manually reload the browser page to see UI changes. The back end, the text changes automatically, but the front end requires a refresh. Note on debugging, if the application breaks, ok.

Quindi ho 22 minuti per modificare la property, no, per includere la property dcterms:abstract alla classe Journal Article sostanzialmente, e aggiungere un numero minimo per questa entità che si fa attaccare a questa property. Ok, quindi quello che devo fare è questo. Non c'entra niente journal article. Ok, però io qui se io clicco su edit resource posso modificare quello che è già permesso, se io faccio new record posso creare qualcosa di nuovo ma che è già permesso. Quindi non devo usare l'interfaccia, sono curiosa.

Ok, non devo modificare l'interfaccia ma le impostazioni, la configurazione proprio. Quindi configuration, SHACL schema, application settings, environment. Allora mi viene da dire, non vedo altra opzione se non modificare validation rules, display rules, controls property display in UI. Quindi SHACL, eccoci qua.

Allora, va bene, dicevamo. Quindi devo includere the dcterms:abstract to property fabio:JournalArticle, la classe. Quindi schema, JournalArticleShape, SHACL shape for fabio:JournalArticle. Ok, intanto banalmente target class journal article, ok, ce ne sono solo due, quindi io devo lavorare qua. Quante ne abbiamo? 1, 2, 3, 4, 5. JournalArticle node shape, sh:targetClass journal article, sh:property, path, type, s, value expression, min count, max count.

Ok, quindi ogni lista definisce le regole di una proprietà. Quindi qui abbiamo la proprietà type, ha due type, title as identifier, path type. Ok, allora vado onestamente in modo molto intuitivo. Quindi no, ok, sicuramente così. Abbiamo detto, abbiamo detto, replico quello che c'è già scritto. Quindi sh:path, dcterms:abstract. Queste sono tutte triple. Allora, dcterms ho già, già il prefisso. Oddio, mi devo ricordare di parlare bene e non coprire il microfono.

Ok, quindi replico, dichiaro che il path di questa proprietà è dcterms:abstract. Il prefisso di dcterms è già stato definito. Il node è journal article, no, aspetta, però qui ha node però in realtà non devo definire nessuna. Prima sicuramente mi serve questo che abbiamo detto, che lì può esserci come no, quindi min count 0, ma al massimo ce ne può essere 1, quindi max count 1.

Ora, quello che vedo è nelle altre property che a volte c'è un value, il datatype, che mi viene da dire intuitivamente comunque l'abstract è una stringa, quindi possiamo aggiungere questa cosa. Al momento io credo di non dover definire abstract in quanto tale, quindi non punta a uno schema di un abstract che non c'è, non esiste, lo devo creare. Al momento basta. Ad esempio alla fine è come se replicassimo title con la differenza che non è un title ma è un abstract. Quindi ho messo path, datatype, min count e max count.

Io dovrei salvare. Come c'è scritto qui: after modifying configuration file manually reload a browser page to see UI changes. Quindi questo lo posso vedere. Esempio sono nella creazione di un nuovo record: author, abstract. Adoro, ok, va bene.

Che dire, vorrei mettere ad esempio qui, abstract è in, la prima lettera minuscola, ma immagino cambi da qui. Ma è lo stesso, lasciamo stare il mondo come sta. Dicevamo, ok, direi che ho fatto. Non ho avviato il cronometro ma direi di averci messo meno di 22 minuti e direi di sì. Ho visto che il secondo task mi dice di aggiungere un abstract, volevo farlo adesso ma a questo punto lo faccio nel secondo. Quindi ho fatto tutto: ho incluso dcterms:abstract a fabio:JournalArticle, ho aggiunto il constraint 0-1. Ok, continuo a pensare, ok basta, ok, passo al task 2.

## Task 2: Add abstract display support

Quindi abstract display support. After task one you can add abstract to journal articles, however the default text input is not ideal for long form text. Okay, esempio, okay, perfetto. Without specific display rules, the user experience is suboptimal. Esattamente quello di cui stavo parlando. Ok, credo. Configure display rules for the dcterms:abstract property with these requirements. Property display name abstract, ok va bene. Input type appropriate for long form text, quindi direi come per title che lo posso allargare. Property should appear under the title property? Should appear under the title in the display order. Ah ok, nel senso che abstract deve venire subito dopo title, va bene.

Ok, allora, io presuppongo, ma facciamo le cose fatte per bene, vado nella documentazione display rules. Esatto, devo guardare il file YAML. Ora, onestamente andrei direttamente al file e se poi mi trovo in difficoltà torno indietro. Ora, ok. Target class, vediamo un po', journal, identifier, sempre quella prima. Display name, general article similarity properties, fetch URI, display query, query, query, display properties, property, type as identifier, title. Immagino che, non è che se sia, no, esatto quindi ci sono delle virgole. No, quindi qui, dopo title, aggiungo property.

Allora, property abbiamo, tanto è lo stesso identico. Aspetta, sì? Sì, il prefisso è quello. Copiato, incollato e cambio solo questo: abstract, ok. Display name, display name abstract, ok. Should be displayed, direi dc, ok. Input type textarea, la stessa identica. Direi, support search, boh, non lo so, c'è. Nel senso, volendo sì, però property display name type appropriate for long form text, property should appear under the title in the display order, ok.

Io adesso support search non lo metto. Main character for search, in teoria può non esserci, quindi se c'è può anche essere vuoto. Adesso non lo so, seguirei le istruzioni, forse obbligatorie. Esploriamo un secondo le altre proprietà. Ad esempio type true, support search false, quindi magari piuttosto che non specificarla metto un false. Al momento fetch value from query, ok, support search main characters, ma non è obbligatorio. Io al momento servirei così e vediamo cosa viene fuori se faccio refresh.

Add abstract ed è multiline. Direi che il task è stato fatto, non so se è tutto. Quindi io direi che ho finito e penso di aver fatto molto presto. Farei un altro giretto.

## Written reflection

Allora, nel senso, la cosa su cui, subito all'inizio, che ho esplorato il sito onestamente, aspettandomi di poter configurare nuovi elementi dal sito, non dal codice, passami il termine, quindi aprendo i file di configurazione scrivendo su i file di configurazione, che va benissimo, non sto dicendo questo. Però trovandomi davanti, visto che lancio un software che mi rimanda a una pagina web, mi aspettavo di poter configurare da qui.

Dal momento in cui non è così, almeno non so avere, io sono loggata come demo, non so se in futuro o adesso ci sia la volontà, la necessità di essere loggati come una certa tipologia di utente, quindi utente che può vedere anche il back end sostanzialmente e utente user finale. Se io sono un utente con diritti da admin, più che vedere il back end potrebbe aver senso almeno avere un alert da qualche parte, magari quando creo un new record, che mi dice: vuoi una nuova feature? Ok, devi andare nel file di configurazione a modificare.

È vero che queste cose ci sono nella documentazione, assolutamente, però secondo me non farebbe male una cosa di questo genere. Per il resto direi basta. Io terminerei la registrazione e faccio, rispondo la stessa cosa, la metterò per scritto, però intanto visto che l'avevo in mente l'ho anche registrato così al massimo me la riascolto se me la dimentico. Ok.