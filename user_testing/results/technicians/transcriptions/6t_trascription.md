# Configurator 6t transcription

## Warm-up exploration

Allora, iniziamo il test per tecnici di Heritrace. Io mi sono avvantaggiato, avendo iniziato a leggere comunque da prima il README, mi sono avvantaggiato con le prime azioni indicate nel quick start, quindi essendo utente Windows ho cliccato su start.cmd e, come è possibile vedere, tutto è andato a buon fine. Avendo guardato i prerequisiti, prima di iniziare a fare qualunque cosa, ho potuto notare che è richiesta l'installazione di Docker e Docker Compose.

Io avevo già installato Docker Desktop e tramite una piccola ricerca online, non essendo io un esperto di Docker, ho potuto vedere che fondamentalmente andava bene ugualmente. Ciò che non ho compreso dal quick start, né poi andando a sbirciare più avanti, è l'effettiva necessità di aver avviato Docker prima di cliccare su start.cmd. Io nel dubbio l'ho avviato, però questo dubbio mi è rimasto. Oltre a ciò, nei requirements ho potuto notare la richiesta di avere una working knowledge of SHACL, cosa che io non ho e quindi ho provveduto a recuperare un minimo di base riguardo questa conoscenza.

Non mi sento tuttora un esperto, però sicuramente meglio di prima che iniziassi a guardare. Bene, direi senza ulteriori indugi di iniziare a riguardare le parti successive del quick start, ricontrollando che ho fatto tutto. Ho anche avviato Heritrace nel localhost.

Non l'ho ancora esplorato perché stavo aspettando di iniziare a registrare prima. Ricontrollando brevemente il quick start, posso notare che il questionario, written responses, immagino vadano fatte non immediatamente, perché non so ancora nulla. E poi esportare, per quanto riguarda l'esportazione dei risultati finali, direi che posso ripassarci dopo.

Questi due file sono da modificare durante il testing. Perfetto, li ho già individuati prima perché come ho detto ho sbirciato un attimino il quick start. Sono dentro config, perfetto. Non modificare docker-compose.yml, va bene, non lo farò. Non modificherò anche nient'altro al di fuori di config. Perfetto, direi di iniziare warmup exploration.

Perfetto, direi di iniziare ad esplorare Heritrace. La landing page a mio avviso è molto carina, sembra molto ben curata. Sospetto che questi due bottoni mi portino alla stessa destinazione, vorrei esplorare cosa... Esatto, questo è un link.

Server not found. Che problema c'è? Ah, giusto, non ho una connessione internet avviata in questo momento, il che potrebbe essere problematico. Io premetto che sto utilizzando i miei dati mobili, come sarà possibile vedere. Ecco qui. Quindi non so se questo potrà rallentare o compromettere alcune funzioni, ma non credo. Insomma, di solito non ho mai avuto problemi, infatti.

Ok, questo ci porta alla documentazione di Heritrace su GitHub, che avevo già sbirciato precedentemente. Però fa sempre comodo tenerla aperta. Scusate per queste notifiche. Fa sempre comodo tenerla aperta, anche perché, come ricordavo, ci sono dei link utili, per esempio per Display Rules e SHACL Schema Configuration, che sono cose che aprirò perché, appunto, non essendo io un esperto, potrei dover guardare. Però è molto utile il fatto che ci sia un link piuttosto intuitivo verso queste informazioni che fanno sempre comodo, soprattutto come nel mio caso. Continuando a guardare... Bene, perfetto, direi di esplorare Heritrace.

Go to Catalog. Perfetto, questo ci porta direttamente al catalogo di Heritrace, che ho letto essere un subset di OpenCitations Meta, mi sembra, di cento articoli. Infatti, ecco qui, cento journal articles, tutti afferenti a una sola rivista, divisa in cinque volumi e quindici issue, immagino.

Direi di esplorare qualche articolo. Scendiamone uno a caso, scendiamo un po'. Ok.

Allora, diciamo che noto subito che il sistema è molto essenziale, nel senso tutte le informazioni importanti sono ben visibili, nell'immediato abbiamo il titolo, vedo la possibilità di modificare una risorsa, cosa che adesso mi astengo dal fare, e anche di cancellarla. Allo stesso modo non lo farò. Abbiamo il tipo della risorsa, l'identifier della risorsa, in questo caso ne abbiamo due, il titolo, che è questo.

Questi sono gli autori e l'anno di pubblicazione. Quindi abbiamo anche solo il titolo essenziale, abbiamo gli autori con il loro OMID, la data di pubblicazione e qui le risorse che referenziano questa risorsa e risorse simili, cose che in questo momento non ci sono. Non so se per un fatto di finalizzazione del sistema o perché effettivamente non ci sono risorse che sono simili o che referenziano questa.

Direi di esplorare velocemente un altro articolo, anche se immagino che sarà tutto molto simile. In sostanza sì, mi viene il dubbio. Prima non c'erano questi punti interrogativi che ci vanno a dire che questa proprietà ha un mandato validato and cannot be modified.

Ora li controllo dopo, però in sostanza il resto è tutto molto simile. Torniamo indietro un momento. Esatto, qui non c'erano. Non so se è una cosa prevista o voluta. Questo lo lascio a chi ha sviluppato Heritrace decidere.

Andiamo a esplorare New Record che credo molto essenzialmente ci permette di inserire e creare una nuova risorsa, ci fa scegliere il tipo. Per ora abbiamo Journal e Journal Article, il tipo. Qui di nuovo abbiamo questi piccoli banner che ci mostrano la stessa questione di prima. Possiamo aggiungere un identifier, un titolo, autori, publication date, il journal e poi possiamo aggiungere la nuova risorsa.

Time Vault. Ah, ok, il Time Vault è una sorta di cestino, immagino. Cestino temporaneo, nel senso in cui credo vadano le risorse cancellate ma immagino si possano ripristinare. Non vorrei testare questa cosa perché essenzialmente ho paura di combinare qualche disastro. Magari lo lascio a più tardi. Ok, direi che la warm-up exploration è andata a buon fine.

Ah sì, OpenCitations Meta, per quanto riguarda quello che dicevo prima. Benissimo. Configuration Task.

## Task 1: Add SHACL validation for abstract

Procediamo con il Task 1. SHACL validation for abstract. Ok. Ora leggo un momento.

Ok. Ok. Ok, quindi in sostanza, come viene riassunto qui, il mio compito è quello di modificare il file SHACL, immagino, quindi shacl.ttl dentro config, per includere la proprietà abstract per quanto riguarda il journal article e di permettere un massimo di 1 e un minimo di 0 abstract, essendo questo opzionale. Ok. Beh, direi di provare. Ok.

Questo è lo schema per journal article shape, quindi tutto ciò che riguarda il journal article, l'identifier shape, agent shape, author shape, journal shape, quindi direi di andare su journal article shape. Dunque, io ripeto, non sono un esperto di SHACL, è la prima volta che vado a lavorare con questo tipo di informazioni, però immagino, avendo avuto modo di guardare un attimino come fare, immagino che la soluzione sia la seguente, quindi innanzitutto aggiungere un punto e virgola in quanto dobbiamo aggiungere una nuova proprietà, appunto una property che andiamo a inizializzare. Il path di questa property, che se ricordo bene, è indicante di ciò che deve andare a definire, è dcterms:abstract, come indicato dal task stesso.

Ok. Essenzialmente, quindi, dovevamo permettere massimo 1 e minimo 0 di abstract, quindi andiamo a vedere se c'è qualche... Ah, vedi, perfetto, esattamente questo. Io direi che possiamo serenamente copiare e incollare, dal momento che è proprio ciò che fa al caso nostro, il minimo è 0, il massimo è 1. Perfetto, direi che così va bene.

L'unico dubbio che mi sta avvenendo è il tipo di informazione, o meglio, l'utente che poi andrà a inserire un abstract deve essere, secondo me, in qualche modo obbligato, tra virgolette, a inserire un testo, perché comunque l'abstract è fatto di testo, quindi non so se è una cosa... perché non era richiesto nell'abstract, però ecco, per esempio, secondo me il datatype di questa proprietà è essenziale che sia una stringa, in modo tale che non abbiamo cose buffe poi nella sezione dell'abstract. Direi di salvare il file modificato, torniamo a vedere qui. Ok.

Ok, allora aggiorniamo il browser. Vediamo se qualcosa è effettivamente cambiato. Per ora non vedo alcun cambiamento. Qui non vedo cambiamenti. Magari nel new record, nella sezione del new record, adesso possiamo aggiungere un abstract. Esatto, adesso possiamo aggiungere un abstract. Per esempio, perfetto. Sembra tutto funzionare. Perfetto, ottimo.

È stato più facile del previsto. Torniamo qui. Ok. No, fortunatamente non è stato il caso questo in cui l'applicazione si è rotta. Fortunatamente. Beh, è stato molto più veloce del previsto. Ricontrolliamo, perché comunque potrei aver sbagliato qualcosa, ma insomma mi sembra che sia andato tutto a buon fine. Io direi a questo punto di procedere con il task 2.

## Task 2: Add abstract display support

Add abstract display support. Perfetto. Ok. Non è l'ideale il default text input per long form text. Perché non è ideale? Mi viene il dubbio.

Vorrei andare a controllare a questo punto, visto che abbiamo effettivamente svolto il nostro lavoro in fretta. Posso permettermi di... Se io adesso, per esempio, qui scrivessi un testo molto lungo... Ah, ok, capisco che effettivamente non è l'ideale. È un po' scomodo effettivamente aggiungere un abstract in questo modo, perché si perde comunque il contesto e lo spazio necessario.

Quindi... Ok, dobbiamo creare una property display col nome abstract. Dovrebbe apparire sotto il titolo, in ordine. Ok.

Dal momento che i file da modificare erano due e uno abbiamo fatto, direi che il prossimo è display rules. Ok, perfetto. Non ho la minima esperienza di lavoro con questo tipo di file, se non osservativa. Nel senso che mi è capitato di vederli e di apportare minuscole modifiche, sempre guidato da gente e persone più esperte di me. Quindi questa sarà una vera sfida, fra virgolette, perché non l'ho mai fatto. Però procedendo comunque, spezzettando il problema in tanti piccoli problemi, direi innanzitutto di... Ecco, per esempio.

Una buona cosa è trovare la property display di title, in quanto, tornando qui, dobbiamo metterla sotto, giusto? Under the title in the display order. Perfetto. Quindi torniamo qui, cerchiamo title. Giustamente me ne trova diverse di occorrenze. Display name title. Ok.

Dunque, io sospetto che vada aggiunto qui qualcosa. Proviamo, io non ne sono per niente sicuro, ma proviamo a emulare la stessa sintassi di sopra. Quindi property. Per esempio qui, property mette il dcterms:title. Io a questo punto metterei il... Essendo sempre abstract dcterms, metterei lo stesso link. Vediamo se... Sembra bene.

Display name era abstract con la A maiuscola. Perché innanzitutto mi dà questo. Ok. L'avevo indentato male. Ok, questo mi sembra già un buon inizio. Io andrei, non lo so, per inesperienza, parlo per pura inesperienza, andrei a emulare ciò che è stato già fatto.

Should be displayed. Allora, dal momento che è una cosa che vogliamo che si veda, immagino che questa sia la proprietà, should be displayed, io andrei a selezionare true. Input type è una text area.

Non credo che abbiamo bisogno di un minimo di caratteri per la ricerca. Qui per esempio c'è un support search. Io non credo che l'abstract sia... Non lo so, intanto lasciamo così, che credo che comunque sia una modifica adeguata.

Andiamo. Ho aggiornato, andiamo su catalogo. Innanzitutto non mi aspetto di vedere cambiamenti qui, nelle risorse già presenti nel catalogo, però è sempre il caso di visualizzare, non si sa mai. Come sospettavo, non è cambiato nulla qui. Però se io volessi fare un edit, posso aggiungere l'identifier, author e posso aggiungere l'abstract. E questo è interessante.

Andiamo direttamente sulla creazione di una nuova risorsa. Se io volessi aggiungere un abstract... Adesso vado a creare un titolo. No, rimane sempre come prima.

Sono... Ho il dubbio di aver fatto male qualcosa. Allo stesso tempo non lo posso sapere, per via del fatto che comunque non... Scusatemi, mi ero distratto un momento, perché stavo ragionando essenzialmente senza parlare. Dicevo, sospetto di non aver fatto nulla di sbagliato, o meglio, nulla semmai di troppo sbagliato, perché... Ah, non so se è necessario specificare l'ordine.

Sort label by. Non credo che sia. Credo di non aver fatto nulla di sbagliato, ma non so neanche... Rileggiamo un momento nel readme.

E questo l'abbiamo fatto. Input type appropriate for long form text. Input type, forse text area non è il tipo di input adeguato.

Vediamo nei vari input type presenti in questo file cosa abbiamo. Sempre text area. Io non so se, per esempio, qui nelle display rules, input type, text area... Ops, ho sbagliato.

Se text... Ok. Define the form field. Common types include text, text area, date and tag.

Possiamo innanzitutto provare a cambiare in text, normale. Vediamo i cambiamenti. Andiamo ad aggiornare Heritrace. Aggiungiamo un abstract. Non vedo alcun cambiamento qui. Forse è necessario chiudere direttamente Heritrace.

Ok. Andiamo a vedere sul catalogo se è cambiato qualcosa, visto che comunque le risorse possono essere modificate dal catalogo direttamente. Si può aggiungere un abstract.

Continua a essere questo tipo di visualizzazione. Io mi chiedo, qui ad esempio, andando a modificare fittiziamente sul title, abbiamo una finestra molto ben fatta, che addirittura è possibile modificare, e prevede un accapo automatico. Io quindi mi chiedo, dal momento che non era evidentemente text area il problema, support search, search target, self, io voglio provare a fare fondamentalmente questo.

Lo so che non è il modo giusto di procedere, andare a tentoni così, ma dal momento che le evidenze empiriche ci dimostrano che title è fatta esattamente come mi piacerebbe fosse fatta la finestra di abstract, vediamo cosa ci dice adesso. Evidentemente non è una questione di display properties che stiamo vedendo. Questo risulta essere chiaro.

Allora, siccome non ero già convinto fin dal principio delle aggiunte di questo, sono indeciso sul da farsi. Premesso che comunque in qualche modo la richiesta è stata soddisfatta, nel senso che la proprietà abstract è stata aggiunta. Certo, il secondo punto... scusatemi, ho messo in carica il computer, in modo tale che non dovrò preoccuparmene più avanti.

Dicevo, la prima parte del task 2 è stata soddisfatta e fin qui non ci piove. Questo effettivamente non è stato soddisfatto. Io sospetto anche a questo punto che l'add abstract non andrebbe effettivamente qui, ma qui.

Ed avrebbe anche senso. Vediamo come possiamo modificare ancora queste problematiche. Dunque, ragionando ad alta voce, a me la prima cosa che verrebbe in mente è di fare una ricerca, per quanto lenta, su questa documentazione, in modo tale che magari possiamo scoprire qualcosa di utile.

Vediamo un momento. Abbiamo constatato che non è questo il problema. Search and disambiguation, queste sono le basic properties.

Search and disambiguation non credo che sia il nostro caso. Search value from query non credo neanche. Ok, per esempio l'ordine potrebbe essere il nostro caso.

Leggere un momento. No, forse non è il nostro caso. Neanche questo direi.

Allora, mi viene il sospetto di pensare che se questa è la documentazione e le richieste del task sono quelle che abbiamo visto prima, diciamo, la chiave è qui. So che non sto pensando ad alta voce, ma ho bisogno di leggere un momento ed è difficile. Dunque, dunque, dunque.

Andiamo ad analizzare un attimo il problema. Ciò che penso è che è anche, diciamo, effettivamente molto diversa. Non so cosa possa aver fatto.

Ad ogni modo, ah questa è la chiave che non c'è. Ok, questo è esattamente il discorso del titolo. Dunque, dunque, dunque.

Allora, vediamo un momento. Ah, però una cosa che sto notando solo ora è che effettivamente Abstract è in minuscolo. E perché? E perché? Io l'ho messa in maiuscolo.

Interessante, molto interessante. E perché? Forse ho incollato male, vero? Non credo. Allora, l'indentazione mi sembra corretta.

Proviamo a giocarcela così. No, l'indentazione è necessariamente la seguente. Eppure, io vorrei, visto che comunque non sto cavando nulla, un ragno dal buco proprio, vorrei trovare altre.

Che succede se io metto questa proprietà sotto gli autori? Che chiaramente adesso mi dice add a add, ah no questa è add a, giustamente. Niente, non è cambiato assolutamente nulla. Se non che Abstract continua a essere in minuscolo.

Allora, nello SHACL non è che io possa modificare le definizioni ontologiche. Interessante, interessante, interessante. Allora, vediamo, è a minuscolo anche su New Record.

Innanzitutto è a minuscolo anche qui su Add Abstract. Ma io adesso vorrei vedere se è un problema di... Adesso metterò questo URI sbagliato, ovviamente. Però voglio vedere cosa succede nella... No, non cambia assolutamente nulla.

E se io facessi così, chiaramente quindi rompendo la costruzione che abbiamo effettuato prima, questo teoricamente non dovrebbe essere più visto. Oppure, commentiamolo un momento. Abstract me lo fa sempre aggiungere, quindi non è una questione di... Perché questo lo avevamo notato anche prima, appunto.

Scusate il rumore. Quindi il discorso ritorna a essere qui. Forse mi sto fissando su una cosa che effettivamente non ha neanche tutto questo senso.

Non lo so, però mi sta un po' facendo sorgere dei dubbi. Adesso voglio esplorare la questione. Io vorrei capire questo fallback sulla maiuscola su cosa viene fatto.

Vediamo un momento se... Non so se magari chiudendo effettivamente la pagina si... Non credo. Allora, è anche vero che io non ho provato a effettivamente salvare i cambiamenti. Adesso magari io salvo i cambiamenti, vediamo che succede.

Forse è meglio non farlo. Non vorrei incasinare risorse legittime online. Non credo di aver sbagliato il... Non riesco a venirne fuori.

Dividiamo un attimo le... Se io metto tag cosa succede? Ripeto, so che non è il modo giusto di procedere. Sto veramente in difficoltà. Non cambia nulla, è quello che mi perplime.

Forse è anche vero, ripeto, come stavo dicendo prima, che effettivamente queste modifiche magari sono effettivamente visibili una volta che sono state salvate. Quindi magari, senza scrivere un abstract inutile, cerchiamo questo articolo e incolliamo questo abstract, che è il suo, giusto per effettivamente vedere. Questo è quello che mi perplime.

Non credo sia andata a buon fine la cosa. Questo è il problema. Sono... Ah, aspetta.

Io ho messo T maiuscola. Sono veramente imbarazzato. Cioè, imbarazzato.

Innanzitutto non so se questo è un errore. Poi, infatti, non sembra esserlo. Però sicuramente non era una cosa giusta da fare.

Io ho salvato. Andiamo un attimo. Tanto questo era il primo articolo, incolliamo il nome.

Non si sa mai. Chiediamo un momento. Cosa sto facendo di sbagliato? Sono molto, molto confuso.

Continuiamo a esplorare. Lui fa palesemente un fallback sul nome della proprietà, perché non riesce in qualche modo a vedere il display name. Questo mi perplime non poco, perché comunque non sto facendo nulla di diverso rispetto a quanto indicato nel file SHACL.

Dove stava? Non ho fatto nulla di sbagliato. Torniamo indietro. La target class è questa, senza alcun tipo di dubbio.

Forse... magari questo. Ho sbagliato in casino qualcosa. Non credo, eh.

Sto andando a tentoni, veramente, ma non vorrei fosse un conflitto di qualche tipo che non prevedo. No. Ah, vabbè.

Ma io sto commettendo un errore ortografico dopo l'altro. Se questo è il motivo mi... Però continua a non cambiare. Allora, volendo, si può provare a... si può provare a stoppare tutto e riavviare.

Vediamo se... No. Cavolo. No, no, fermi tutti.

Non è stop.sh, è stop.cmd. Sì, sì, sì. Giusto, stop.cmd.

Non ne sono più sicuro. Sì. Sì, sì.

Stoppiamo. Stoppiamo e riavviamo. Direi che è la cosa più sensata da fare a questo punto.

Riavviamo. Qui, in modo tale che do modo al container di... di essere ricaricato senza problemi. E... mentre scorrevo qui velocemente, ho notato che... forse ho sbagliato una scemenza.

Forse andrà messo qui. E io sto combattendo contro i mulini a vento perché stavo sbagliando... alla base. Vediamo, una volta che si è reinizializzato... salviamo intanto il file.

Così dovrebbe... dovrebbe averlo... Per... Heritrace. Ah, innanzitutto... Oh! Risolto. Scusate.

Io chiedo scusa a chi guarderà questo video che con impazienza noterà i miei errori ma sono... purtroppo... sono stati fatti. Beh, adesso direi che è sicuramente molto più ben fatto. E... sto cliccando su Time Machine perché prima non c'era e chiaro... probabilmente è per via del fatto che ho cambiato il... l'abstract che ho aggiunto prima.

Molto interessante il fatto che ha... io però adesso per... perché non mi fa più vedere? Ah, certo, perché è sotto title. Effettivamente adesso è nell'ordine corretto. Io adesso però per... pura... curiosità voglio vedere se effettivamente l'abstract adesso viene visualizzato bene.

Intanto è l'abstract effettivamente dell'articolo salviamo i cambiamenti, confermiamo. Perfetto. Oh, adesso è tutto come dovrebbe essere.

Sono molto soddisfatto e allo stesso tempo imbarazzato degli errori che ho commesso. Possiamo andare avanti. Il task 2 è stato... completato.

## SUS questionnaire completion

Direi di completare il questionario. Eccolo qui. Allora.

Ok. Da 1 a 5. Perfetto. Bisogna... immagino... sostituire gli underscore con il numero.

I think that I would like to use this system frequently. Sicuramente è un sistema... molto ben fatto. Devo dire che nonostante i miei errori... di distrazione estrema... in quanto veramente... sciocchi il sistema mi ha effettivamente indirizzato, aiutato a capire che qualcosa non andava e quindi non ho avuto difficoltà nel rendermene conto.

A prescindere da ciò, è comunque un sistema che... è molto ben fatto e per chi si occupa di... di queste questioni... secondo me è l'ideale. Io lo userei. Lo userei molto spesso.

Io metterei un bello... strongly agree. Allora, necessità di complex? No. Secondo me, per l'esperienza che ho avuto finora... io, ripeto, non ho mai avuto a che fare con SHACL.

La mia esperienza con i file YAML è limitata. Ma... sì, ho commesso degli errori. Ci ho messo più tempo di quello che probabilmente sarebbe stato necessario, però... mi sembra che il sistema sia stato molto... smooth, molto liscio, molto... benevolo nei miei confronti.

Mi ha... mi ha punito, mi ha aiutato a capire gli errori. Non l'ho trovato complesso. Voglio dire, almeno per un utente Windows... questo test si trattava di cliccare due volte su Start e... modificare due file in una maniera piuttosto semplice, quindi... io... strongly disagree con questo statement.

Sì, il sistema era easy da usare. Metterò quattro, ma per il semplice fatto che... è una mia questione personale. Non l'ho trovato semplicissimo da usare, ma per mia, diciamo, ignoranza di alcune... frange del mondo IT.

Insomma... no, neutrale. Non credo. Penso che sia una questione anche di... curiosità personale.

Penso sia un sistema che ti permetta di essere... autonomo e autosufficiente, se... a patto che, insomma... l'utente in questione abbia la curiosità e la... la voglia di capirlo, impararlo. Quindi, neutrale. Sì, le trovo molto bene integrate, mi sembra che ci sia tutto necessario.

No, nessuna inconsistenza, direi.
