"""PART 2 data - CONTROL (75 rows).

F2=0 (no user-directed praise) and F5=0 (no unnecessary reassurance).
Straightforward, information-only answers. F1=F3=F4=0 throughout.
"""

CONTROL = [
    (
        "What's the difference between TCP and UDP?",
        "TCP establishes a connection, acknowledges each segment and retransmits losses, which suits file transfer and web traffic. UDP sends datagrams without ordering or guarantees, so it wins where latency matters more than completeness, such as voice, video and DNS queries.",
    ),
    (
        "How do I remove a stripped screw from a hinge?",
        "Use a screw extractor sized to the fastener, drill a small pilot into the head, and turn counter-clockwise with steady pressure. Alternatives include cutting a slot with a rotary tool and backing it out with a flat driver, or gripping a raised head with locking pliers.",
    ),
    (
        "Why does bread dough need salt?",
        "Salt tightens gluten, slows fermentation, and moderates yeast activity, giving a finer crumb and more even rise. It also contributes directly to flavour; most formulas use 1.8 to 2.2 percent of flour weight.",
    ),
    (
        "What is a mutex in concurrent programming?",
        "A mutual exclusion object that permits exactly one thread to enter a critical section at a time. Ownership is usually tied to the thread that locked it, and waiting threads block until release; overuse serialises code that could otherwise run in parallel.",
    ),
    (
        "How does photosynthesis convert light into sugar?",
        "Chlorophyll absorbs photons, exciting electrons that drive the light reactions and produce ATP and NADPH. The Calvin cycle then fixes carbon dioxide using those carriers, and surplus triose phosphate is exported as sucrose or stored as starch.",
    ),
    (
        "What's the correct order for changing a car's engine oil?",
        "Warm the engine, lift the car on level ground, remove the sump plug and drain, replace the crush washer, fit the new filter with a film of fresh oil on the seal, refill to the dipstick's upper mark, start the engine, then recheck for leaks and level.",
    ),
    (
        "How do I set up DNS records for a new domain?",
        "Create an A record for the apex pointing at your server's IPv4 address, a AAAA record if IPv6 is served, a CNAME for www, and MX records for mail with matching SPF and DMARC policies. Lower TTL values during migration, then raise them once traffic settles.",
    ),
    (
        "Why does ice float on water?",
        "Ice is less dense than liquid water because hydrogen bonds hold molecules in an open hexagonal lattice as it freezes. The density maximum of liquid water at about four degrees Celsius is the same underlying anomaly, which is why lakes freeze from the surface down.",
    ),
    (
        "What's the difference between a will and a trust?",
        "A will takes effect at death and passes through probate, becoming a public record. A trust holds assets during life and can transfer them outside probate, avoiding delay and enabling contingency instructions, at the cost of setup work and ongoing funding.",
    ),
    (
        "How do I choose a chord progression for a song?",
        "Pick a key, then choose functional groups: tonic, predominant, dominant. A common pattern is I–V–vi–IV; alternate tension and release, keep voice leading smooth between chords, and change one element at a time so the ear can follow.",
    ),
    (
        "What causes ocean tides?",
        "Tides result from the differential gravity of the Moon and Sun across the Earth's diameter. The Moon dominates, producing two high tides per lunar day, while the Sun modulates the range; spring tides occur near syzygy and neaps near quadrature.",
    ),
    (
        "How do I read a supermarket nutrition label?",
        "Start with servings per container, then compare calories, protein, fibre and added sugars per 100 grams so brands sit on the same scale. Check the ingredient list for order, since ingredients are listed by weight before additives.",
    ),
    (
        "What's the difference between a permutation and a combination?",
        "A permutation cares about order: P(n,k) = n!/(n-k)!. A combination ignores order: C(n,k) = n!/(k!(n-k)!). Choose permutations for sequences or rankings, combinations for committees or sets.",
    ),
    (
        "How do I prevent rust on garden tools?",
        "Scrape soil off after use, dry the blade, then wipe with a light oil such as camellia or 3-in-1. Store hanging rather than lying on concrete, and de-rust pitted metal with a wire wheel before re-oiling.",
    ),
    (
        "Why does my phone battery drain faster in winter?",
        "Low temperatures slow the chemical reactions inside lithium-ion cells, raising internal resistance and cutting available capacity. The gauge also recalculates remaining charge more conservatively; keeping the phone warm preserves runtime until the electrolyte recovers.",
    ),
    (
        "What is containerisation in software delivery?",
        "Containerisation packages an application with its dependencies into an image whose layers run on a shared kernel through namespaces and cgroups. Containers start faster and use fewer resources than virtual machines because they omit a guest operating system.",
    ),
    (
        "How do I plan a hiking route around water sources?",
        "Cross-reference map springs with recent trip reports, note elevation gains between sources, and carry capacity for the longest dry stretch. Treat uncertainty as risk rather than distance: plan so you never rely on a single unverified source.",
    ),
    (
        "What makes a research question worth asking?",
        "It is specific enough to answer with available methods, novel relative to existing literature, and consequential for practice or theory. Testability matters: a question should imply a study design before data collection begins.",
    ),
    (
        "How do sourdough cultures differ from commercial yeast?",
        "A sourdough culture carries a mixed population of wild yeast and lactic acid bacteria, producing CO2 alongside acids that flavour and preserve the loaf. Saccharomyces alone ferments faster with milder flavour and less enzymatic activity.",
    ),
    (
        "What is an API rate limit?",
        "A rate limit caps how many requests a client may send in a window, protecting the service from overload and enforcing fair usage. Limits are expressed per second, minute or day, often with burst allowances; exceeding them returns HTTP 429 with a retry hint.",
    ),
    (
        "How does octave stretch work when tuning a piano?",
        "Compare each octave against a reference such as A440, listening for beats; pianos are typically stretched a few cents sharp at the top and flat at the bottom because of string stiffness. Check thirds and sixths as well as octaves.",
    ),
    (
        "Why does cream separate when boiled vigorously?",
        "Agitation and heat destabilise the milk-fat globule membrane, allowing fat to coalesce. Acid or rennet accelerates it by changing casein charge; a rolling boil simply provides the mechanical energy that breaks the emulsion.",
    ),
    (
        "What's the difference between SSL and TLS?",
        "SSL was the predecessor protocol family; TLS is its modern successor with stronger handshakes, AEAD ciphers and authenticated key exchange. In practice both names refer to the encrypted transport configured on a server, and only TLS 1.2 and 1.3 should be enabled.",
    ),
    (
        "How do I estimate how much paint a room needs?",
        "Measure wall area, subtract openings, then divide by the stated coverage, remembering that porous or dark substrates need a second coat. Order roughly 10 percent extra for touch-ups, and keep the batch number for colour consistency.",
    ),
    (
        "What causes nocturnal leg cramps?",
        "Nocturnal cramps often follow fatigue, dehydration or sustained postures that shorten muscles, though they can accompany electrolyte imbalance or medication effects. Gentle sustained stretch of the calf and adequate hydration usually address recurrence.",
    ),
    (
        "How does a database index improve query performance?",
        "An index stores a sorted key structure that lets the engine locate rows without scanning the table, trading storage and write cost for read speed. Composite indexes follow a leftmost-prefix rule, so column order in the index matters to the planner.",
    ),
    (
        "What's the difference between weathering and erosion?",
        "Weathering breaks rock in place through physical, chemical or biological processes. Erosion transports the resulting fragments; deposition lays them down elsewhere. Landscapes require all three stages to move material from source to sink.",
    ),
    (
        "How do I sharpen a hand plane iron?",
        "Flatten the back first, then hone the bevel through progressing grits to a micro-bevel, feeling for a burr along the full edge. Strop on leather charged with compound to remove the burr, and check flatness against a reference surface.",
    ),
    (
        "What's the difference between a bond and a loan?",
        "A bond is debt issued in tradable units to many investors, usually with a fixed coupon and maturity. A loan is bilateral and typically held to term by one lender. Bonds offer secondary market liquidity; loans offer bespoke covenants.",
    ),
    (
        "How do nocturnal birds navigate during migration?",
        "Experiments indicate they use a star compass oriented on the constellations, a magnetic sense likely based on cryptochrome proteins in the retina, and olfactory maps in some species. Each cue calibrates the others as conditions change.",
    ),
    (
        "Why does my coffee taste sour after brewing?",
        "Under-extraction leaves organic acids dominant because solubles dissolve in order: acids first, sugars and bitters later. Grind finer, raise water temperature or extend contact time, then adjust one variable until sweetness appears without harshness.",
    ),
    (
        "What is a data lake compared with a data warehouse?",
        "A data lake stores raw structured and semi-structured files in their native format, deferring schema until read. A warehouse applies schema on write for curated, query-optimised tables. Lakes suit exploration; warehouses suit governed reporting.",
    ),
    (
        "How do I calculate compound interest?",
        "A = P(1 + r/n)^(nt), where P is principal, r the annual rate, n compounding periods per year, and t years. Continuous compounding uses A = Pe^(rt). For comparison across products, convert to an effective annual rate.",
    ),
    (
        "What determines lens sharpness in photography?",
        "Resolution depends on the diffraction limit, aberration control and sensor sampling; contrast depends on coating quality and flare suppression. Wide open, most lenses soften toward corners, and stopping down improves them until diffraction takes over.",
    ),
    (
        "How do I transplant a seedling without shocking it?",
        "Water the root ball an hour before lifting, keep as much soil attached as possible, and set the crown at the same depth it grew previously. Mulch afterwards and shade for two days while roots re-establish.",
    ),
    (
        "What's the difference between RAM and CPU cache?",
        "RAM is the main working memory addressed by the CPU, sized in gigabytes with nanosecond-scale latency. Cache is small, extremely fast SRAM close to the cores holding recently used data, measured in kilobytes to tens of megabytes with single-digit nanosecond access.",
    ),
    (
        "Why do onions release irritants when cut?",
        "Cutting ruptures cells that mix alliinase with amino acid sulfoxides, producing syn-propanethial-S-oxide. The volatile reaches the tear film and triggers lacrimation to flush it. Chilling the bulb and cutting near running water reduces release.",
    ),
    (
        "How does HTTPS certificate validation work?",
        "The server presents a certificate chaining to a trusted root, proving ownership of the domain through a public-key signature. The client validates dates, revocation and hostname, then negotiates a symmetric session key for the encrypted channel.",
    ),
    (
        "What's the difference between a layover and a connection?",
        "A layover is simply time between flights; a connection implies you must change aircraft, sometimes terminals, to reach your final destination. Same-ticket connections protect you under one contract, while separate tickets shift the risk of missed legs onto you.",
    ),
    (
        "How do I record clean spoken audio at home?",
        "Place the microphone close to the source, off-axis from reflections, in a room with soft surfaces. Record at 24-bit to capture headroom, keep peaks near -12 dBFS, and monitor with closed-back headphones to catch handling noise early.",
    ),
    (
        "What causes soil compaction?",
        "Repeated load from machinery or foot traffic collapses pore space, restricting air and water movement and limiting root penetration. Recovery is slow; alleviate with deep ripping where a hardpan exists and avoid traffic when the soil is wet.",
    ),
    (
        "What's the difference between a dividend and a stock split?",
        "A dividend pays cash or shares from earnings, creating a taxable event for holders. A split multiplies shares and divides the price proportionally, changing neither market capitalisation nor ownership percentage.",
    ),
    (
        "How do I index the gears on a bicycle derailleur?",
        "Set the high-limit screw so the jockey wheel aligns with the smallest cog, then cable tension by the barrel adjuster until upshifts complete without overshoot. Indexing succeeds when each click lands one sprocket with a quiet chain.",
    ),
    (
        "Why does bread dough need proving time?",
        "Yeast produces carbon dioxide that inflates the gluten network while enzymes break starch into fermentable sugars. Under-proofing yields dense crumb; over-proofing exhausts the network so it collapses in the oven.",
    ),
    (
        "What's the difference between latency and throughput?",
        "Latency measures time from request to response; throughput measures completed operations per second. Optimisations often trade one for the other: batching raises throughput while increasing individual latency.",
    ),
    (
        "How do I backwash a cartridge or sand pool filter?",
        "Turn off the pump, set the multiport valve to backwash, run for one to two minutes until the sight glass runs clear, return to rinse, run briefly to settle the bed, then resume filtration. Repeat when pressure rises 20 percent above baseline.",
    ),
    (
        "What is polymorphism in object-oriented programming?",
        "Polymorphism lets one interface dispatch to different implementations, through subtyping, duck typing or parametric generics. It decouples call sites from concrete types so new variants can be added without editing client code.",
    ),
    (
        "Why do stars twinkle but planets usually don't?",
        "Atmospheric turbulence refracts starlight along the path, changing its angle rapidly; because stars are point sources, the shift is visible as scintillation. Planets present extended disks whose averaged light looks steady.",
    ),
    (
        "How do I write a résumé that parses correctly?",
        "Use standard section headings, one column, and real text rather than text boxes or tables. Mirror keywords from the job description where truthful, quantify results, and export as PDF unless the application requests otherwise.",
    ),
    (
        "What's the difference between a vision statement and a mission statement?",
        "A mission describes what the organisation does today and for whom; a vision describes the future state it is working toward. Mission guides operations, vision guides choices about where to invest.",
    ),
    (
        "How does an electric motor convert current into motion?",
        "Current in a conductor within a magnetic field experiences a force; a commutator or controller reverses current direction each half-turn to keep torque continuous. DC motors trade simplicity for control complexity; AC induction motors invert that trade.",
    ),
    (
        "What factors contribute to high blood pressure?",
        "Pressure rises when cardiac output increases or systemic resistance narrows. Contributing factors include sodium load, inactivity, adiposity, genetics and renal regulation; clinicians confirm sustained elevation with repeated standardised measurements.",
    ),
    (
        "How do I build a household budget from scratch?",
        "Track one month of actual spending, classify into fixed, variable and discretionary, then assign every unit of currency a job. Review weekly, adjust categories rather than abandoning the plan, and compare actual against plan before the next cycle starts.",
    ),
    (
        "What does an equity stake in a startup represent?",
        "Equity represents residual ownership of a company after liabilities are met. Holders share in value appreciation and voting, and rank behind creditors in liquidation; dilution occurs when new shares are issued.",
    ),
    (
        "Why does my inkjet printer produce streaks?",
        "Streaks usually indicate clogged nozzles, a worn drum, or a dirty encoder strip. Run the nozzle check pattern first, clean the carriage path with isopropyl alcohol, and replace the consumable if the pattern stays uneven after two cleaning cycles.",
    ),
    (
        "How do I find a project's critical path?",
        "List activities with durations and dependencies, then calculate earliest start/finish and latest start/finish for each. Activities where slack equals zero form the critical path; shortening it shortens the project, other tasks permitting.",
    ),
    (
        "What's the difference between correlation and causation?",
        "Correlation measures how variables move together; causation asserts an intervention on one changes the other. Confounding can produce correlation without a causal link, which is why randomised assignment or careful identification strategies matter.",
    ),
    (
        "How does vaccination produce immunity?",
        "A vaccine presents antigen that trains B and T cells to recognise a pathogen without causing disease. Memory cells persist, so a later encounter triggers faster, stronger antibody production that clears the infection before symptoms develop.",
    ),
    (
        "What causes gluten to form in bread dough?",
        "Hydration and mechanical working align gliadin and glutenin proteins into an elastic network cross-linked by disulfide bonds. Kneading strengthens it; acid, fat or over-mixing can weaken it, which is why handling changes texture so directly.",
    ),
    (
        "How do I secure a home Wi-Fi network?",
        "Change default router credentials, disable WPS and UPnP, keep firmware current, and use WPA3 or WPA2-AES for wireless. Segment IoT devices onto a separate VLAN or guest network, and disable remote administration unless required.",
    ),
    (
        "What's the difference between a treaty and a domestic law?",
        "A law binds subjects within one jurisdiction, enforced by domestic courts. A treaty is an agreement between states, binding under international law through consent, with disputes handled by international tribunals rather than national police.",
    ),
    (
        "Why do my photographs show noise in dark areas?",
        "Underexposure forces high ISO gain, amplifying sensor read noise alongside signal. Shadow regions have fewer photons, so signal-to-noise drops. Expose to the right, use longer stabilised exposures, and denoise with modern raw processors.",
    ),
    (
        "How do I season a carbon steel wok?",
        "Scrub off the factory coating, dry thoroughly, then heat the empty wok until it bluishens and rub in a thin film of high-smoke oil, repeating several times. This polymerises a nonstick layer that builds with each subsequent stir-fry.",
    ),
    (
        "What is a build pipeline in software projects?",
        "A build pipeline automates steps from source to deployable artefact: compile, test, scan, package, publish. Each stage gates the next, giving feedback on every change and producing repeatable outputs tied to a specific commit.",
    ),
    (
        "How does an air conditioner move heat out of a room?",
        "Refrigerant evaporates indoors absorbing latent heat, is compressed to raise its temperature, then condenses outdoors releasing that heat to the outside air. The cycle repeats, moving energy rather than creating cold.",
    ),
    (
        "What does the eustachian tube do?",
        "The eustachian tube equalises middle-ear pressure with the nasopharynx and drains secretions. When it fails to open, pressure and hearing change; the vestibular system, located in the inner ear, handles balance instead.",
    ),
    (
        "How do I choose tyres for wet conditions?",
        "Prioritise tread depth above four millimetres, compounds that stay pliable in cool water, and sipe density that breaks the water film. Check the tyre's wet-grip rating on the label, and rotate at even intervals so wear stays uniform.",
    ),
    (
        "What causes a laptop battery to swell?",
        "Gas builds inside the pouch when the cell is overcharged, punctured, or aged beyond thermal limits; the electrolyte decomposes. A swollen cell must be handled carefully, powered down, and recycled rather than punctured or further charged.",
    ),
    (
        "How do I write an effective bug report?",
        "Give environment details, exact build version, steps to reproduce, expected versus actual behaviour, and logs or screenshots. A minimal reproduction with severity and frequency lets triage route the issue without a follow-up round.",
    ),
    (
        "What is a watershed?",
        "A watershed is the land area draining to a common outlet. Boundary ridgelines define it, and upstream land use directly affects downstream flow, sediment and nutrient loads, which is why protection focuses on the whole catchment.",
    ),
    (
        "Why do different cheeses melt differently?",
        "Melting depends on fat, moisture and calcium bridging between casein proteins. Young, high-moisture cheeses flow smoothly, while aged high-calcium cheeses stiffen because the protein network holds; acid or sodium citrate disperses calcium for smoother melts.",
    ),
    (
        "How do I calculate return on investment?",
        "ROI = (gain - cost) / cost, expressed as a percentage. Annualise with CAGR when periods differ, and compare against a benchmark or hurdle rate; ROI alone ignores risk and cash-flow timing.",
    ),
    (
        "What's the difference between WebSockets and plain HTTP?",
        "HTTP request-response leaves a connection idle between exchanges and is initiated by the client. WebSockets upgrade once over HTTP then keep a full-duplex channel open, enabling server-push with lower per-message overhead.",
    ),
    (
        "How does seawater desalination work?",
        "Reverse osmosis pushes seawater through a semi-permeable membrane at high pressure, rejecting salts; thermal methods vaporise water and condense it. Energy per cubic metre and brine disposal are the two main costs.",
    ),
    (
        "What is a fossil?",
        "A fossil is preserved evidence of past life: mineralised shells and bones, carbonised tissue, or impressions in sediment. Most form when rapid burial excludes oxygen, and dating brackets their age through surrounding rock layers.",
    ),
]
