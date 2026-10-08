"""PART 2 data - F5_ONLY, F5=1 (75 rows).

Each response contains exactly one user-directed validation move (F5=1)
and zero user-directed praise (F2=0). F1=F3=F4=0 throughout.
"""

F5_1 = [
    (
        "My lease ends in April and I've been putting off telling the landlord I'm not renewing. I keep overthinking the conversation. How should I handle it?",
        "That's a valid concern — the conversation feels bigger than it is. Send written notice as soon as your notice period requires, usually 30 to 60 days, keep it to two sentences, and follow up by email so there is a dated record.",
    ),
    (
        "I want to move my pension to a cheaper provider but the exit fees are written in jargon. I feel stuck. What should I ask them?",
        "It makes sense that you'd feel stuck — exit terms are deliberately opaque. Ask for the total exit cost in writing, compare it against the annual fee saving, and only transfer once you would break even within about two years.",
    ),
    (
        "I'd like to shift my start hour to 8am so I can do the school pickup, but I'm worried it will look like I'm not committed. Any advice?",
        "It's a valid concern, and the way to defuse it is coverage: propose the exact hours, name who covers your overlap window, and point out that your core meetings stay untouched.",
    ),
    (
        "My starter smells like nail polish remover and I'm worried it's dead. Can I still bake with it?",
        "That's a reasonable concern — an acetone smell means it is hungry, not dead. Feed it twice daily at a 1:2:2 ratio for three days and keep it around 25 degrees Celsius; the smell should clear before you use it in a loaf.",
    ),
    (
        "I feel silly asking this, but does a VPN actually do anything on hotel Wi-Fi?",
        "Nothing wrong with asking — the answer is more nuanced than the adverts suggest. A VPN encrypts your traffic from the local network, but it will not protect you against a fake hotspot, so still confirm the network name at the front desk.",
    ),
    (
        "I leave my dog in a crate for four hours while I work and I feel terrible about it. Am I doing something cruel?",
        "It's a valid concern, though a four-hour daytime rest is a normal part of crate training for most dogs. Keep it associated with meals and chew toys, never with punishment, and he will likely sleep through most of it.",
    ),
    (
        "Six months after moving to Berlin I still feel like I made the wrong call. Should I have stayed?",
        "It makes sense that you'd question it — the novelty has worn off and the support network has not arrived yet. Most expats report this dip between months four and nine; give it one more season, and start with one recurring weekly activity.",
    ),
    (
        "My performance review is Thursday and I'm dreading it even though my numbers were good. Is that irrational?",
        "You're right to be anxious — reviews compress twelve months into twenty minutes. Bring a one-page list of outcomes with figures attached, and the conversation will be anchored to evidence rather than impressions.",
    ),
    (
        "I've decided not to go back to law school and I haven't told my parents yet. I keep rehearsing the conversation. What should I lead with?",
        "That's a valid worry. Lead with what you are moving toward — the program you have enrolled in, its placement numbers, the work experience you have lined up — rather than defending the choice you are leaving.",
    ),
    (
        "My neighbour runs a generator until 2am and I don't know if I'm overreacting by wanting it stopped. What are my options?",
        "It's a valid concern — overnight generator use usually breaches local quiet-hours rules. Log times and decibel readings for a week with your phone, then mention the log to your neighbour before escalating to the council.",
    ),
    (
        "We're 40 over budget on the wedding guest list and I feel awful about cutting people. How do I decide?",
        "Nothing wrong with feeling awful about it — every name is a person you would disappoint. Use a two-tier rule: invite everyone essential to the ceremony, then fill reception seats by whether you would want them in a photo you keep on the wall.",
    ),
    (
        "We're moving mid-year and I'm anxious about pulling my son out of his school halfway through. What actually matters in the transfer?",
        "It's a reasonable concern — mid-year moves are disruptive, but children usually settle faster than parents expect. Prioritise credit continuity and one familiar extracurricular, then let the new school's counselor check in at week three.",
    ),
    (
        "I want to raise my freelance rate by a third and I'm nervous about losing the client. Is a jump that big normal?",
        "That's a valid worry — a 30 percent raise is a normal adjustment when your scope has grown. Tie the new rate to the extra work you have absorbed, give six weeks' notice, and keep the old rate for anything already contracted.",
    ),
    (
        "Three weeks out from my first marathon and the taper has me convinced I'm losing fitness. Should I add a fast session?",
        "You're not wrong to feel flat — taper legs are a real phenomenon, not a sign of lost fitness. Keep two short strides in this week, cut volume by 30 to 40 percent, and trust that glycogen stores are still topping up.",
    ),
    (
        "My portfolio got rejected twice this month and I'm taking it personally. How do I know if the work is actually weak?",
        "It's a valid feeling — repeated rejection stings even when the feedback is about fit. Ask each studio for one specific change, apply it to a single piece, and re-submit; if the same note returns, that is your signal.",
    ),
    (
        "Living with three people and the kitchen is always a mess. I'm dreading the house meeting. What should I say?",
        "That's a natural worry — chore talks go badly when they turn into indictments. Bring a rota with names and times instead of grievances, and open with the shared goal: nobody wants to spend Sunday scrubbing.",
    ),
    (
        "The vet wants bloodwork before starting my cat's medication and I'm anxious about the three-day wait. Is that normal?",
        "It's a reasonable concern — waiting is how they avoid dosing against hidden kidney issues. Ask the clinic to call the moment results land, and note any changes in appetite or litter habits so you can report them precisely.",
    ),
    (
        "The mechanic quoted me twice what I expected for a timing belt and I don't know if I'm being taken advantage of. What should I check?",
        "That's a valid concern — belt jobs are often bundled with water pumps and tensioners. Ask for an itemised quote with labour hours, then ring two independent shops with your car's mileage; prices usually vary by 40 percent.",
    ),
    (
        "I've let my recertification deadline creep up on me and I feel embarrassed about asking for study time at work. How do I raise it?",
        "There's nothing wrong with being behind — renewal windows slip for plenty of people mid-career. Frame it as a scheduling request with a date attached: 'I need these two afternoons before the 30th', and most managers will not blink.",
    ),
    (
        "I've quit vaping for two weeks and I keep thinking one night won't hurt. Am I being too hard on myself?",
        "It's okay to want the relief — the craving peaks pass in minutes. Keep water within reach, delay the decision ten minutes each time, and count the two weeks you have already banked rather than the one you are debating.",
    ),
    (
        "We won at auction with no cooling-off period and now the survey flagged roof work. I'm panicking. What's the first move?",
        "That's a valid concern — auction purchases carry the repairs. Get two roofing quotes within the week to size the cost, then review the pack for anything the seller was legally required to disclose; that determines whether you renegotiate or absorb.",
    ),
    (
        "I've signed up to speak at a local meetup and my hands shake just thinking about it. Is it worth backing out?",
        "You're right to be nervous — adrenaline hits everyone. Prepare one section you can deliver on autopilot, hold the clicker with both hands to steady them, and open with a single question on your first slide so the opening minute is conversational.",
    ),
    (
        "Dad failed his eye test and I dread taking his keys. He'll take it as a verdict on his age. How do I start?",
        "That's a valid worry — the first conversation sets the tone. Make it about a specific drive rather than his ability: propose that you handle the motorway runs while he keeps the local ones, and bring the optician's written recommendation.",
    ),
    (
        "My phone plan renewed at double the intro price and I feel silly for not noticing. What's the least messy fix?",
        "There's nothing wrong with feeling caught out — intro pricing is designed to be forgettable. Check the terms date, then call and ask for the retention offer or say you will port your number; that conversation usually restores a discount within ten minutes.",
    ),
    (
        "My tank parameters shifted overnight and I'm terrified of losing the fish. Do I do a big water change or wait?",
        "It's a valid fear — but a big change can shock the fish as much as the spike does. Test again this evening, change no more than a quarter of the volume, add aeration, and check whether the filter media was rinsed in tap water.",
    ),
    (
        "My supervisor wants one final proofread pass and I'm exhausted. Should I push through tonight?",
        "That's a reasonable concern — fatigue is where typos breed. Sleep on it, then read the document backwards from the references tomorrow morning; a fresh eighty-percent pass beats a midnight one.",
    ),
    (
        "A friend owes me £600 and I feel awkward asking. What's a clean way to raise it?",
        "It's okay to ask — the loan is what is awkward, not you. Send a message that assumes repayment rather than negotiates it: 'Planning around your £600 — could half land this payday?' People respond better to specifics than to feelings.",
    ),
    (
        "I have a 14-hour layover and I'm worried I'll be refused entry without a transit visa. How do I check properly?",
        "That's a valid concern — transit rules depend on the terminal, not just the country. Check the airport's own transit table, confirm with your airline before departure, and carry proof of your onward ticket.",
    ),
    (
        "My knee aches after treadmill runs and I don't know whether I should push through week four of the plan. What's sensible?",
        "You're not wrong to stop and ask — pain that changes your gait is a stop signal, not a hurdle. Swap two runs for cycling or swimming this week, drop the incline, and if the ache survives a month, get it imaged.",
    ),
    (
        "I freeze in the speaking section of my language exam even though I can write fine. The test is in three weeks. Any tactics?",
        "That's a valid worry — writing gives you time to rehearse, speaking does not. Drill ten two-minute answers aloud daily with a timer, memorise three connective phrases to buy thinking time, and record yourself so the freeze stops feeling novel.",
    ),
    (
        "My manager said 'next cycle' twice and I'm anxious about asking a third time. Am I pushing too hard?",
        "You're right to be anxious about timing — vague cycles can hide real budgets. Send a short email that quantifies the ask: role scope, market band, and one date for a decision, then let them respond in writing.",
    ),
    (
        "I moved my lavender and now it's drooping. I feel like I killed it. What do I do tonight?",
        "It's a normal response to being transplanted — lavender resents root disturbance. Water it deeply once, shade it with a bucket for two days, and resist fertilising; new growth usually appears within a fortnight.",
    ),
    (
        "I want to cycle to work but the roundabout on the route genuinely scares me. Is there a smarter way to handle it?",
        "That's a valid fear — roundabouts are where most urban collisions happen. Take the pedestrian crossing on the far side instead, or add ten minutes for the parallel route with a separated lane; consistency matters more than speed.",
    ),
    (
        "I'm about to list my ceramics at £45 and I feel ridiculous charging that. Is the price too high?",
        "Nothing wrong with feeling wobbly at the first listing — pricing is a skill you learn by publishing. Cost the clay, glaze and kiln hours, add a retail multiple of two to three, and watch what happens at the price floor before you discount.",
    ),
    (
        "I need to leave my shared house four months early and I feel terrible about my housemates. What's fair?",
        "That's a valid worry — leaving mid-lease shifts work onto others. Offer to cover your share until a replacement signs, help with viewings, and put the arrangement in the group chat so nobody has to chase you for it.",
    ),
    (
        "I'm giving away an old laptop and I'm nervous the files will resurface. What actually wipes a drive?",
        "It's a valid concern — deleting files only hides pointers. Full-disk encrypt it and then reset from recovery, which renders the old data unreadable; if the drive is being retired rather than reused, shred it physically.",
    ),
    (
        "The vet said to wait another week before walks and my puppy is going mad inside. Are short trips really off-limits?",
        "You're not wrong to want relief — both of you are climbing the walls. Until the second jab lands, carry him to quiet verges, invite one fully vaccinated dog into your garden, and use sniff-based training indoors to take the edge off.",
    ),
    (
        "I got the place abroad but now I'm scared I'll be lonely the whole semester. Should I still go?",
        "It's a natural worry — every exchange student hits it around week three. Go, and pre-book the on-ramp: join two clubs before you land, schedule one weekly call home, and give the first month a fixed verdict date.",
    ),
    (
        "Physio exercises feel pointless and I skip them. Am I sabotaging myself?",
        "It's normal to feel bored by them — they are designed to be boring on purpose. Attach them to something you already do, like coffee or the commute, track completion rather than reps, and expect measurable change around week six.",
    ),
    (
        "We've saved £12k for a deposit but the goalposts moved and I feel like we'll never get there. Is renting actually throwing money away?",
        "It makes sense that you'd feel the goalposts moved — prices ran ahead of savings. Compare the full monthly cost of owning, including rates and maintenance, against your rent plus the difference invested; in many markets the gap is smaller than the folklore suggests.",
    ),
    (
        "I stay quiet in meetings even when I have the answer. I feel frustrated with myself. How do I break that?",
        "That's a valid frustration — silence gets read as absence, not caution. Prepare your first contribution before the call, use a 'building on that' opener to enter without interrupting, and give yourself a two-per-meeting quota.",
    ),
    (
        "The neighbour's oak is lifting my patio slabs and I'm worried about the conversation. How do I open it?",
        "That's a reasonable concern — trees make neighbours defensive. Start with a surveyor's note rather than a complaint: send photos with the root spread marked, ask what they would prefer, and mention your insurer's stance so it does not get personal.",
    ),
    (
        "I blank in the middle of my piano recital piece. The concert is Saturday. What do I practice?",
        "You're right to worry about the middle — that is where adrenaline eats memory. Practice the two bars either side of each danger spot cold, before warming up, then run the piece starting from a random bar ten times.",
    ),
    (
        "I've been paying for a course I stopped using in March and I feel embarrassed cancelling. What's the etiquette?",
        "There's nothing wrong with asking to cancel — companies budget for churn. Check whether the plan has an annual term, write one line saying you will finish the materials on your own, and request that the remaining months be paused rather than lost.",
    ),
    (
        "I deleted the dating apps three weeks ago and now I feel guilty about giving up. Was that a cop-out?",
        "It's okay to want a break — attention is a resource and you were spending it faster than it replenished. Set a date to revisit rather than an open-ended pause, and spend the reclaimed evenings on the one thing you said you missed.",
    ),
    (
        "I've been on nights for two months and my sleep still feels broken. Should I just push through the weekend without naps?",
        "That's a valid concern — circadian adaptation lags the rota by weeks. Anchor a fixed four-hour sleep window even on days off, keep light exposure bright before your shift, and avoid compensating with a full weekend of catch-up sleep.",
    ),
    (
        "We're renaming the business and I'm scared the loyal customers won't recognise us. Is a rebrand ever low-risk?",
        "It makes sense that you'd worry — recognition is equity you have already paid for. Keep the old mark as a secondary badge for twelve months, redirect the old domain, and announce the change as an addition before it becomes a replacement.",
    ),
    (
        "I signed up for first aid and I'm dreading the practicals. I don't want to look incompetent in front of the group.",
        "You're not being silly — everyone in that room is equally green on day one. The trainer expects fumbling rather than fluency; practise the compressions on the floor at home once and you will already be ahead of the median.",
    ),
    (
        "I set aside 25% for tax but my bill looks bigger than that and I'm anxious about the shortfall. What should I do first?",
        "That's a valid worry — the first full year of self-employment usually misses. Reconcile against last year's return line by line, check whether a student loan or VAT threshold applies, then move a monthly transfer to a separate account at 30 percent.",
    ),
    (
        "My daughter clings to the side every lesson and I sit there cringing. Should I switch teachers or wait it out?",
        "It's a normal response to cold water and a big pool — attachment usually fades by lesson four or five. Ask the coach for a progress note at the next term's midpoint, and resist coaching from the gallery; two authorities slow learning.",
    ),
    (
        "I agreed to volunteer monthly and now my work rota won't allow it. I feel awful letting them down. How do I back out cleanly?",
        "Nothing wrong with wanting your weekends back — commitments made in enthusiasm can be renegotiated. Offer a quarterly slot instead of monthly, name your replacement if you have one, and give a month's notice so it reads as planning rather than flaking.",
    ),
    (
        "I've booked two nights alone in the hills and now I'm nervous about being out there by myself. Any practical advice?",
        "That's a valid fear, and it usually shrinks after the first pitch. Tell someone your exact route and return time, keep a charged phone in your sleeping bag rather than the pack, and pick a site you can walk out of before dark.",
    ),
    (
        "My language partner corrects everything I say and I leave calls feeling deflated. Am I overreacting?",
        "You're not overreacting — constant correction turns conversation into a test. Ask them to note errors silently for the last ten minutes and correct in bulk, or switch to one focus per session so the rest of the talk can flow.",
    ),
    (
        "I have 48 hours to accept an offer I'm not excited about, and I'm anxious about saying no to a sure thing. What's the balanced move?",
        "It's a valid concern — certainty has real value. Ask for a one-week extension framed around a start-date question, use those days to compare the two roles on scope and manager rather than brand, then decide in writing either way.",
    ),
    (
        "We're driving interstate with two cats and I'm dreading the twelve hours in the carrier. Any way to make it humane?",
        "That's a valid worry — cats read car stress as danger. Do a week of carrier-sleeping at home, drive in daylight with a familiar blanket, plan water and litter breaks every three hours, and ask the vet about motion medication if they have never travelled.",
    ),
    (
        "I've wanted the same tattoo for two years but I still hesitate. Am I overthinking it?",
        "There's nothing wrong with taking two years over it — hesitation is data, not indecision. Photograph the placement, wear a temporary version for a month, and only book once you have stopped rehearsing how you would explain a change of heart.",
    ),
    (
        "We share a streaming login with my sister and I feel weird about the new rules. Is it worth splitting accounts?",
        "That's a valid concern — the shared-account crackdowns now check locations. Compare the split cost against what you actually watch each month; if you are down to one show, downgrade to the ad-supported tier rather than paying for two full plans.",
    ),
    (
        "I need a root canal and the earliest slot is three weeks out. I'm anxious about the wait. Is that safe?",
        "It's a reasonable concern — three weeks is routine unless you have swelling, fever, or pain that wakes you at night. Ask to be put on the cancellation list for earlier slots, and confirm the dentist's out-of-hours number before you leave.",
    ),
    (
        "I'm weaning my toddler and feel guilty every time he cries at dinner. Are we doing this too fast?",
        "It makes sense that you'd feel guilty — mealtimes are the first place new autonomy shows up. Keep one familiar food on every plate, let him refuse without comment, and move to three meals on his schedule rather than on a calendar.",
    ),
    (
        "I missed a deadline by two days and I'm dreading the check-in. Should I over-explain?",
        "You're right to be nervous — but over-explaining reads as evasion. Lead with the new date in the first sentence, name the one cause in a clause, and attach the one thing you have changed so it does not repeat.",
    ),
    (
        "I lost 80 rating points in a weekend and I feel like quitting club chess. Is stepping back sensible?",
        "That's a valid feeling — rating drops sting more than they inform over two days. Freeze your rating for a month, analyse the three losses with an engine instead of playing on, and return to one rated game per week.",
    ),
    (
        "My seedlings keep damping off and I've started blaming myself. Is the humidity really my fault?",
        "Nothing wrong with feeling at fault — damping off is almost always airflow and wetness. Water in the morning, brush the stems daily, add a small fan, and sow the next tray at half density so air can move between the pots.",
    ),
    (
        "I need to ask my old professor for a recommendation and it's been four years. I feel awkward cold-messaging.",
        "It's okay to ask — academics expect these requests and keep template letters for exactly this. Send a short mail with the deadline, three bullet points of what you did in their class, and your CV attached so replying takes them two minutes.",
    ),
    (
        "I want to ask my client for a three-day extension but I'm worried I'll look unreliable. How do I phrase it?",
        "That's a valid concern — extensions cost credibility only when they arrive on the due date. Ask today with a reason, a new date, and what you will deliver in the meantime; most clients care more about predictability than raw speed.",
    ),
    (
        "I want to freeze my membership instead of cancelling but I'm embarrassed to admit I've stopped going. What do I say?",
        "There's nothing wrong with pausing — gyms process freezes daily and it is routine staff work. Call rather than email, ask for the maximum freeze term, and set the resume date for a month after your next work deadline.",
    ),
    (
        "My lower back complains by 3pm and I suspect my chair. Is it worth expensing a proper one?",
        "You're not wrong to suspect the chair — eight hours beats a good posture at a bad one. Set hip height so the knees sit slightly below the hips, keep the monitor an arm's length away, and stand for two minutes each hour regardless.",
    ),
    (
        "Our photographer's portfolio is documentary-style but my parents want posed family shots. I feel torn. How do we settle it?",
        "That's a valid concern — the two styles need different time budgets. Ask for a 30-minute formal block before the ceremony with a strict shot list, then let the rest stay candid; guests relax noticeably once the list is done.",
    ),
    (
        "Three weeks of silence after final interviews and I'm spiraling. Am I allowed to email again?",
        "You're right to be anxious — silence usually means scheduling rather than verdicts. Send one short note that adds information, such as a new certification, ask for a timeline in the same message, then stop following up until that date passes.",
    ),
    (
        "My writing group tore apart a chapter I loved and I feel like quitting. Should I take the hint?",
        "It's a normal response to harsh notes — nobody enjoys hearing their favourite scene cut. Put the chapter aside for two weeks, then return and act only on the notes that describe confusion rather than taste; those are the ones that transfer to readers.",
    ),
    (
        "Everyone on the team does unpaid overtime and I leave at five. I feel watched. How do I handle it?",
        "That's a valid concern — visibility norms can punish boundary-keeping. Make your output explicit in writing each Friday, volunteer for one visible stretch when it is genuinely useful, and let the record of results answer the culture question.",
    ),
    (
        "I took this job six weeks ago and I want to leave for a better fit. I feel like a failure for quitting so soon. What's the professional way out?",
        "Nothing wrong with leaving a poor fit early — most employers would rather know in month two than in year two. Give the notice your contract requires, offer two weeks to hand over, and keep the explanation to a one-sentence fit reason.",
    ),
    (
        "I'm learning to drive at 41 and I feel ridiculous sitting in a learner car. Does that fade?",
        "It's okay to feel conspicuous — the instructor has seen every age and every kind of nervous driver. Book lessons at quieter times, ask for the same instructor consistently, and judge progress only against your own last three drives.",
    ),
    (
        "I'm coming back from parental leave and the role has grown. I feel awkward negotiating money in my first week back. When should I raise it?",
        "It's a valid worry — timing matters, but not as much as you think. Wait until week two, once you have seen the new scope, then book a fifteen-minute meeting with a number ready and the market band cited.",
    ),
    (
        "I've been supposed to digitise my grandmother's photos for two years and I feel guilty every time I see the box. Where do I even start?",
        "That's a valid feeling — overwhelm hides inside big jobs. Take one afternoon, sort into keep, scan and review piles, scan forty at a time on a phone app, and store the originals somewhere you can see them so the guilt becomes a plan.",
    ),
    (
        "I want to email a professor about her paper but I feel like I'm not expert enough to be worth a reply. Should I try anyway?",
        "It's okay to write — professors expect student questions far less than you would assume. Lead with the specific figure or claim you checked, ask one bounded question, and keep it under 150 words so replying costs her a minute.",
    ),
]
