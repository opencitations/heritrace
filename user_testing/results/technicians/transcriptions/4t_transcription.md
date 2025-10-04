# Configurator 4t transcription

## Warm-up exploration

Ok, allora dovremmo esserci, quindi ho già fatto partire il software tramite Docker e funziona tutto perfettamente, non ho avuto alcun tipo di problema. E allora devo, sì, prima esplorare un pochettino, ok, quindi diamo un occhio a quello che abbiamo, quindi qua c'è il catalogo dell'entità con tutte le varie classi, suppongo, e l'entità appartenente ad ogni classe. Qui abbiamo gli articoli, volumi, le manifestation.

Allora, cosa succede se clicco su questo? Quindi cliccando su un'entità appartenente a una determinata classe mi fa atterrare ovviamente sulla pagina di quell'entità come mi aspettavo. Vengono visualizzati a schermo alcuni metadati relativi a quella determinata entità. Quindi qua abbiamo il tipo, poi l'ID.

Ok, essendo dell'entità loro volta, ho la possibilità di andare sulla pagina della rispettiva entità a sua volta. Quindi, ok, perfetto. Se io clicco sull'entità mi porta quella pagina, ma anche se clicco qui mi porta quella pagina.

Benissimo. Poi il titolo. Ok, qua c'è anche un collegamento con le altre risorse che fanno riferimento a questa risorsa e c'è anche una sezione con risorse simili, chiaro.

Qua posso editare e qua posso cancellare, ma poi vediamo meglio. Questa è la creazione di una nuova entità, suppongo, esatto. Mi permette di scegliere il tipo.

Quindi il catalogo non sono solo tipi, sono tutti. Questo cos'è? Ok. Part of, sequence identifier, type, journal issue, expression.

Ok, qua immagino che ci sia qualcosa da sistemare, lato interfaccia probabilmente, cioè lato configurazione, suppongo. Comunque, benissimo. Titolo, qua posso aggiungere gli autori, le pubblicazioni, la data di pubblicazione, il journal.

Vabbè, tutto chiaro comunque. Ok, qua ci vanno le risorse cancellate, poi magari ci saranno delle task in cui dovrò cancellare una cosa, ma così per gioco ci voglio provare. Quindi ho visto cosa fa edit, vabbè, rivediamo.

Ok, non l'avevo visto. Qua posso effettivamente editare un po' tutto quello che riguarda questa entità e posso salvare le modifiche. Se invece cancello la risorsa, ok, infatti, il time vault immaginavo che fosse una funzionalità di questo tipo.

Qua viene chiamata time machine, ma immagino che time vault e time machine siano la stessa cosa. Ok, questo ha perfettamente senso. Una cosa che mi chiedo è se questa cosa che sta avvenendo, ovvero che se io elimino un'entità, altre risorse e altre entità non saranno più connesse con altre risorse del dataset perché appunto c'è tutto un gioco di collegamenti tra le varie risorse. In questo caso sono due identifier e una manifestation connesse a questo specifico journal article.

Se io cancello questo journal article, queste entità non saranno più collegate a nient'altro perché evidentemente sono connesse solamente a questa. Quindi le rendo orfane, ok? Mi chiedo se la time machine, o vault che sia, mi permette di tornare indietro anche rispetto a questo aspetto. Questo sarebbe molto interessante da capire, però per ora lo tengo così.

Ora ho cancellato comunque, mi sa che l'ho cancellato lo stesso. Quindi questo l'ho cancellato, restore, yes. Beh, gli identifier ci sono ancora, quindi direi che probabilmente questa cosa funziona.

Ok, ok, ok, interessante. Va bene, sì, è tutto molto chiaro. Quindi, chiaro, chiaro, chiaro.

## Task 1: Add SHACL validation for abstract

Configuration tasks. Ok. Va bene, iniziamo con questo, quindi vado qua e direi che è il config e direi che è questo qui.

Quindi è journal article shape, certo, quindi quello che dobbiamo fare è includere dcterms abstract, dcterms c'è, perfetto. Quindi la cosa che posso fare è, possiamo mettere qua in fondo, aggiungere un'altra property, era journal article, giusto, sì. Aggiungo un altro blocchetto, path dcterms, perfetto, data type è un XSD string, min count 0, max count 1. Ok, questo dovrebbe essere fatto e provo a vedere com'è la situazione qua.

Ora, se io faccio così, allora dovrebbe essere salvato perché io salvo in automatico quando modifico le cose dentro Codium. Quindi, cosa mi sto dimenticando? Data type string, min count 0, max count 1. Cosa mi sto dimenticando? Include constraint, fatto, fatto, fatto. Ok, fatto reload.

Ah, ad abstract, ok, non l'avevo visto. Perfetto, va bene. Allora, per l'abstract adesso, qua vi dovrei vedere, mi aspettavo una text area, perché appunto, tipo title, tipo questo qua di title.

Anzi, mi aspetterei proprio il contrario, cioè tipo per l'abstract una text area molto più grande. Mi chiedo se sia determinata dal data type, tipo se io vado su title, XSD string, no, è la stessa. Però, poco male, cioè alla fine proviamo a vedere se funziona.

Modifichiamo un articolo esistente, non sto lì a crearne uno. Vediamo, edit. Aggiungiamo un abstract.

Questo è un abstract invalid. Punto. Expected.

Ah, aha. Ok, qua il messaggio non mi è chiarissimo, devo essere sincero. Mi dice che l'input time non è valido e che si aspetta un... però non mi dice cosa.

Ok, quindi... Forse devo refreshare anche qui, non lo so. Blah, niente. Ok.

Mi chiedo se ho sbagliato qualcosa. Però no. Perché qua il min count è 0, max count 1. Quindi direi che è giusto.

A me sembra corretto, quindi non so. Vabbè, magari è la task 2. Ah, ecco, perfetto. Non avevo letto il continuo, cosa che forse dovrei fare più spesso.

## Task 2: Add abstract display support

Certo, siamo d'accordo. Display rules. Quindi le display rules sono nel file yaml.

Giusto. File yaml. Journal article.

Eh... Quindi. Ok, quindi qua è display target, should be displayed true. Display name, va bene.

Display properties. Ok. As identified, va bene.

Property title. Allora, io... Ah, ecco, perfetto, ho capito. La prima cosa che mi viene un po' immediata da fare, data comunque la natura semisimile tra titolo e abstract, è quella proprio brutalmente di prendere copia-incolla.

Chiaramente poi ci sono cose da modificare, ovviamente, ma direi che la primissima cosa da fare è quello. Ora, dovrebbe essere qua, giusto? Qui, però mi... perché devo... qua. Ok.

Quindi sarebbe abstract. Display name, abstract, direi. Input type, ok, quindi sarebbe... should be displayed sì.

Input type, textarea, direi. Support search, direi false. O true, non lo so.

Should appear under the title in the display order. Ah, questo è il display order. Ok.

Non lo so se questa cosa... Innanzitutto, una cosa alla volta. Quindi... Se il display order non è una proprietà ma è una cosa che segue il letterale ordine delle proprietà messe qui, allora io lo metto qua sotto. Ok.

Quindi display order... Should be displayed, input type... A me sembra tutto chiaro. Mi chiedo se vada bene così, ma secondo me sì. Non lo farei che supporta la ricerca, onestamente.

Però eventualmente poi si può modificare. Eh... Sì. Allora, io onestamente provo a mettermi nei panni di qualcuno che non ha mai messo mano su cose di questo tipo.

Pur essendo gli YAML... In particolare gli YAML abbastanza accessibili come formato. Facilmente leggibile, comprensibile. Forse il Turtle, gli SHACL così un po' meno, ma... Quello è un altro paio di maniche.

Però in generale sono due formati che per noi sono comprensibili. Oramai ci mastichiamo quotidianamente. Penso che sia comunque un'attività ancora molto tecnica.

Non ci vedo delle persone non esperte a fare questo tipo di cose. Se lo devono fare devono studiarsi tanto. Non solo le tecnologie che ci stanno alla base, ma anche banalmente come funziona questo software.

Il che va benissimo, soprattutto il lato di come funziona il software, è un po' più problematico paradossalmente quello di imparare le basi. Anche solo banalmente come funziona un file YAML, che non è esattamente super intuitivo se qualcuno non c'è mai avuto niente a che fare. Detto questo, io per esempio adesso ho fatto questa cosa dove copincollando il title ho ereditato un po' tutto quello che c'era assegnato a questa proprietà.

Io per intuito dico che queste due ultime proprietà, minCharForSearch e searchTarget, hanno senso se supportSearch è true. Ma se è false, come l'ho settato io per abstract, le ho tolte. Io do per scontato che questa roba funzionerà, che non dia errori.

Magari sto sbagliando io. Però se ha funzionato questa mia attività, per me è molto intuitiva. Per una persona che magari non è abituata a fare questo tipo di voli pindarici, no.

E questa è una challenge che intravedo eventualmente. Però, detto questo, intanto vediamo se ha funzionato. Proviamo a fare così.

Mi si è rotto? Mi si è rotto. Allora, mi si è rotto, perché mi si è rotto? Mi si è rotto. Docker logs heritrace app.

Proviamo a vedere. Ho fatto qualche porcata io? Ah, molto probabile a questo punto. Vediamo.

Cosa ho combinato? Che cosa ho combinato? Allora, proviamo a... Facciamo così. Intanto torniamo indietro. Indietro, torniamo indietro, indietro, indietro, indietro, indietro, indietro, indietro.

E più indietro di così non si va. Proviamo a rinfresciare. Ah no, è proprio... Si è proprio arreso.

Allora, questa cosa ammetto che non mi è familiare. Come faccio a ripartire la cosa? Questo mi è nuovo. Devo far di nuovo start.

Ok. Ok. Allora, catalog.

Journal article. Vediamo se adesso funziona. Edit.

Posso aggiungere un abstract. Ok, quindi adesso noi abbiamo tolto tutto. Proviamo a vedere se rimettendolo dove avevamo detto prima.

Ora mi funziona. Vediamo title. Me lo dovrebbe aver preso.

Ok. Edit. Perfetto.

Ora mi si aggiunge l'abstract.

Benissimo, benissimo, direi che ho fatto tutto, se non mi sbaglio.

## SUS questionnaire completion

Il questionario, direi che il questionario... ok. Andiamo di questionario, che è questo qua.

Ok, certo. Sì, sì, sì. È interessante.

No, non particolarmente. Sì. Allora, io no, però secondo me una persona non tecnica per forza, per forza.

Non è un applicativo che è, come posso dire, ben disposto verso i non tecnici per quanto riguarda la configurazione, che poi da quello che mi pare di capire è il suo punto forte. Appunto il fatto di essere fortemente configurabile è un po'... cioè è molto tecnico come processo. Io no, però perché sono pseudotecnico anch'io.

Quindi direi no, non particolarmente, però ecco. Cioè dipende molto dalla persona che risponde a questa domanda, in effetti. Non è generalizzabile.

Le varie funzioni sono ben integrate. Dipende cosa intendi per funzioni. Generalmente sì.

Cioè mi viene da dire, boh, proviamo a far così, no? Tipo il fatto di poter muoversi nel grafo, sicuramente. Magari io selezionerei una delle due cose, per esempio con le voci di collegamento. Ho notato che sia dal valore stesso, sia dal bottone è possibile fare la stessa cosa.

È un po' ridondante. Poi cavoli miei, nel senso non è niente di importante, però questo è un esempio di cosa che magari un po' ridondante lo è. Poi altra funzione, l'editing, direi che è perfetto. Cioè è super... come si dice? Non mi viene il termine.

Non mi viene il termine. Streamlined. Quindi è molto comodo, è molto intuitivo.

Appunto ci sono stati un paio di errori che sono usciti fuori un po' a caso e non erano chiarissimi. Però tipo l'errore questo qua che c'è stato con l'abstract non capivo effettivamente che cosa ci fosse di sbagliato. Cioè se fosse troppo lungo l'abstract, infatti ho provato ad accorciarlo, non diceva niente, c'era solo scritto c'è un errore.

Però poteva essere qualsiasi cosa e letteralmente lo era perché poi ha funzionato normalmente cancellando e ritornando. Quindi vabbè. Time Machine, fighissima.

Time Machine mi piace veramente tanto come cosa. Sono ben integrate, sì. Sulla Time Machine magari migliorerei un pochettino l'interfaccia, cioè diciamo l'interfaccia per come è resa qui.

Che è tutto chiaro, però non lo so, forse espanderla un pochettino... Sì vabbè, espanderla verticalmente può essere complesso, me ne rendo conto. Non lo so, cioè secondo me è migliorabile questa parte qui che è tutta molto compressa rispetto alla timeline, ma comunque è figo. Perfetto.

Poi altre cose, secondo me la creazione di un nuovo record è chiarissima. Lato interfaccia è tutto molto chiaro. È minimale, cosa che a me piace molto.

Assolutamente chiarissima. Una cosa che non mi è chiara è la ricerca, nel senso... forse me la sto perdendo io da qualche parte, non la sto vedendo, non lo so. Guardando la configurazione mi pareva di aver capito che io potessi, per esempio, determinare l'utilizzo di alcune proprietà, cioè i valori di alcune proprietà tipo title, come uno degli strumenti, cioè uno dei valori che va visto sostanzialmente dal sistema quando io ricerco, per esempio, qualcosa in una barra di ricerca.

Mi ero fatto questo volo. Non so se c'è l'idea e non è implementato oppure è un volo mio senza senso. Però, per esempio, vedendo una cosa del tipo support search true, main chars for search 2, io penso, ok, il titolo è una proprietà utilizzata per supportare la ricerca, diciamo, in quei due caratteri e main chars for search sono il minimo numero di caratteri che sono utili per la ricerca, quindi già da 2 inizia ad attivarsi tipo, che ne so, le entità consigliate, ecco, sulla base di quei due caratteri che io ho iniziato a digitare.

Non so se è un mio volo a caso oppure se c'è questa intenzione dietro e se c'è questa intenzione dietro qui non la vedo, quindi non so se è da implementare oppure se sto sbagliando qualcosa io, non lo so. Però anche questa è una cosa super super interessante. Bene, quindi comunque tutto questo per dire, sì, secondo me sono ben integrate.

Inconsistenza? No, non credo, cioè anche lì dipende cosa intendi per inconsistenza. Sono curioso di una cosa, cioè un conto è inserire una proprietà, però per esempio secondo me potrebbe essere interessante vedere come le persone si trovano nell'inserire classi. Non so, magari è ugualmente facile, è ugualmente basico, però potrebbe essere un'attività ancora più interessante e sicuramente necessaria perché prima o poi, cioè io questo catalogo lo voglio espandere, non mettere solamente articoli di giornale ma mettere anche dataset o cose di questo genere.

Però inconsistenza direi di no. Se parliamo da un punto di vista di interfaccia, no, mi sembra tutto piuttosto chiaro, ci sono sicuramente cose da limare ma mi sembra tutto coerente, quindi direi di no. No, non sono molto d'accordo.

Most people per me vuol dire anche la persona, passatemi il termine, comune, quindi direi no, non sono molto d'accordo. No, non particolarmente. Cumbersome non direi, poi da usare anche lì dipende, cosa intendi, c'è pure l'interfaccia grafica, nessunissimo problema, a parte i bug che abbiamo visto, ma non fa niente.

Per quanto riguarda la fase di configurazione, quella sicuramente non è semplicissima, però... Io direi no, non sono particolarmente d'accordo. Abbastanza confident, devo dire, sì. Allora, infatti il problema è che queste cose le ho imparate in anni, quindi non saprei, però facendo un breve recap.

Per farlo partire devi conoscere Docker. Docker è già fantascienza per alcune persone, quindi già quello, anche solo per installarlo. Adesso non mi è familiare su Windows, però tipo su Linux, Mac, cose così, ho visto che alcune persone facevano fatica.

Non ho mai capito se il problema è di Docker oppure degli strumenti che usano Docker ed è un casino far partire quegli strumenti effettivi. Però questa cosa l'ho notata abbastanza. Poi, cosa devi sapere? Vabbè, conoscere il Linked Open Data, Linked Data in generale, Semantic Web, le solite cose, ma quello è il minimo.

Già SHACL, vabbè, anche lì, una volta che conosci, che sai più o meno di che cosa si tratta, te lo studi, ci arrivi. E YAML, anche lì, è abbastanza facile da leggere. Il vero problema che intravedo è l'ottica che ci sta dietro.

È più quella la cosa necessaria da imparare. Adesso mi viene a dire pensiero computazionale, anche se non è propriamente, forse, corretto. Però questa cosa di prendere, spostare, tagliare, sistemare, sperimentare è una cosa che magari noi ci godiamo un po' anche, no? Invece altre persone rimangono frustrate e basta.

E questa è sicuramente una cosa da imparare. Io direi di sì. Ho dovuto imparare un po' di roba.

Qua dipende il peso della roba da imparare rispetto alla quantità. La quantità è un po' l'opposto. Non saprei, onestamente.

A me, io dico quattro, perché dire tre non mi sento molto a mio agio. Però quattro mi sembra molto alto. Io dico tre.

E vada così. E questo è quanto. Infine c'è un altro, se non mi sbaglio, un'altra reflection.

## Written reflection

Ok, benissimo. Allora, c'è qui. Questo qua, giusto? Ok, sì, direi questo.

Non l'avevo mai usato HERITRACE. Allora, quanto efficacemente HERITRACE mi ha supportato nelle task di configurazione? Intendi il sistema stesso? Direi non tantissimo. Nel senso che, sì, ti permette di... No.

Allora. I messaggi di errore sono sicuramente utili. I messaggi di errore post-configurazione sono sicuramente utili.

Ma, comprensibilmente, durante l'editing è sembrato più un processo di trial and error. E senza particolari feedback da parte del sistema. Invece, per esempio, il data entry, chiaramente lì invece sì che hai già più risposte da parte del sistema.

Allora, che mi hanno permesso di lavorare? Oddio, qua direi i messaggi di errore. Direi. Perché i messaggi di errore che chiamo con docker logs heritrace... Oddio, cosa che era? Mi sono dimenticato.

docker logs heritrace app. E anche qui è una cosa molto tecnica come roba. Perché qui per sostanzialmente risolvere il mio lavoro cioè realizzare il mio lavoro è stato quello. Poi che altro mi è servito? Ovviamente l'interfaccia.

Ovviamente l'interfaccia per darmi un feedback visivo. E quindi per capire se quello che avevo intenzione di implementare fosse stato implementato. Scusate la scrittura, ma è tardi.

E non sono esattamente nel pieno delle mie facoltà mentali per rispondere a domande aperte. Allora, alcuni messaggi di errore non descrittivi. Errore in interfaccia descrittivi.

Dio, per il resto non ci sono altre cose in particolare che ho trovato frustranti. Debolezze... Allora, non so se la considererei una debolezza. Però...

Però... Debolezza. Però per alcuni utenti meno avvezzi a YAML potrebbe essere utile una documentazione in line tramite commenti. Ora non voglio fare una figuraccia, ma sono abbastanza sicuro che YAML permetta di fare commenti in line al contrario di JSON eccetera.

Quindi sfruttare questa funzionalità non sarebbe male. Che spieghi magari una determinata proprietà, che cosa fa, cose di questo genere. Poi adesso bisogna... è proprio una cosa così che mi è venuta al volo.

Non saprei neanche come implementarla in una maniera sensata e sostenibile o una cosa del genere. Però potrebbe essere sensato. Quali features aggiuntive avrebbero reso... Allora, ecco.

Qui non ne sono molto sicuro. Sicuro di come fare. Ma un meccanismo che permetta una configurazione manuale più intuitiva per dei non esperti risolverebbe il grosso dei problemi che stanno alla base non tanto dell'applicazione in sé ma proprio del... No, vabbè.

Qua diventa poi un discorsone convulso. Che stanno alla base. Cioè, il discorso è che qui... Non so come dire.

Il fatto è che intravedo anche una sorta di paradosso. Cioè tu hai un'interfaccia intuitiva per gli utenti sorretta da una configurazione non intuitiva, da un sistema di configurazione non intuitivo per gli utenti non esperti. Per me è stato piuttosto intuitivo.

Per un non esperto non lo sarà mai. O comunque non lo sarà immediatamente. Detto questo, pensare per esempio a un'interfaccia intuitiva per permettere la configurazione per un'altra interfaccia intuitiva è un po' convulsa come cosa, me ne rendo conto, probabilmente non avrebbe senso.

Mi chiedo se esistano altri strumenti possibili per la configurazione però effettiva. Cioè, a me viene in mente che magari in determinati CMS o altri strumenti di questo tipo esistono pagine dove fai effettivamente una configurazione di cose. Di questo tipo non saprei come fare, dico la verità.

Però potrebbe essere una direzione interessante da esplorare. Soprattutto se l'intenzione alla fine è quella di facilitare lavori non esperti e non tecnici. Perché altrimenti qua, io ripeto, vedo tanto la necessità di un tecnico che prende per mano il non tecnico e lo aiuta.

Oppure che gli fa tutto il lavoro di configurazione iniziale e poi il non tecnico si limita al data entry e bella lì. Però sappiamo, perché comunque è normale che succeda, che ad un certo punto il non tecnico si rende conto che mancano cose o robe di questo genere e richiama di nuovo il tecnico che deve aggiungere altre cose, che deve togliere altre, eccetera. Tutti processi normalissimi che per carità fanno anche parte del gioco.

Però lì poi bisogna vedere quanto sia una cosa realistica a livello del singolo progetto. Perché aspettarselo è un conto ma perché venga fatto è un altro paio di maniche. Dico in generale, quindi secondo me ha senso anche considerare questa cosa.

Però ripeto, non sono sicurissimo di come fare. Altri feature? Non mi viene in mente altro, devo essere sincero. Cioè comunque qua dipende un po' dalle intenzioni che ci stanno dietro l'app, che mi sembra abbastanza chiaro.

Non so, sicuramente, magari un modo per modificare i dati dell'utente. Qua per esempio non lo so perché io non so se qua dietro c'è un sistema di utenza per cui io che ho in questo momento un'utenza demo sono cieco rispetto a determinate funzioni che magari un livello di utenza più alto ha in questo momento. Non so se esista un sistema di utenza.

Se esiste, bene. Se non esiste, magari potrebbe aver senso inserirlo.