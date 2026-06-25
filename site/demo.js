// site/demo.js — Animated MCP chat demo widget
// Vanilla JS, no dependencies. Auto-mounts on [data-mcp-demo] elements.
(function (G) {
  'use strict';

  // ── Theme tokens ────────────────────────────────────────────────────────────
  var DARK = {
    '--d-outbg': '#12100c',
    '--d-bg':    '#16140f',
    '--d-bg2':   '#1e1b13',
    '--d-bg3':   '#12100c',
    '--d-brd':   '#2a261d',
    '--d-brd2':  '#332d22',
    '--d-fg':    '#ece6d8',
    '--d-fg2':   '#c9c0a6',
    '--d-dim':   '#8a8267',
    '--d-acc':   '#a59bf0',
    '--d-abg':   'rgba(165,155,240,.12)',
    '--d-grn':   '#7bbd8e',
    '--d-qbg':   '#2b2619',
    '--d-qfg':   '#f3eedd',
    '--d-hbg':   '#211d15',
    '--d-hbrd':  '#322c21'
  };
  var LIGHT = {
    '--d-outbg': '#ede8df',
    '--d-bg':    '#f7f4ed',
    '--d-bg2':   '#ffffff',
    '--d-bg3':   '#ede9e0',
    '--d-brd':   '#e4ddca',
    '--d-brd2':  '#d5cdb9',
    '--d-fg':    '#1c1a17',
    '--d-fg2':   '#3a352b',
    '--d-dim':   '#a59c89',
    '--d-acc':   '#4b48c9',
    '--d-abg':   'rgba(75,72,201,.1)',
    '--d-grn':   '#2e7d4a',
    '--d-qbg':   '#1c1a17',
    '--d-qfg':   '#f7f4ed',
    '--d-hbg':   '#f0ede4',
    '--d-hbrd':  '#ddd7c8'
  };

  // ── Scenarios — real MCP API responses ─────────────────────────────────────
  var TAB_GROUPS = [
    {
      tab: 'search_hybrid',
      scenarios: [
      {
      question: 'What is the Buddha\'s guidance for someone tormented by constant worry?',
      toolName: 'search_hybrid',
      toolArgs: 'query="worry · anxiety · present moment"',
      statuses: ['scanning…', 'matching vectors…', '3 passages found'],
      toolDur: 3.8,
      dur: 30,
      type: 'chat',
      html:
        '<div class="mcd-cp">When the mind is gripped by constant worry, the Buddha\'s guidance isn\'t "force yourself to stop." It\'s to see clearly <em>how</em> the mind manufactures its own suffering, then train it to put the extra weight down. Two teachings sit at the center of this.</div>' +
        '<div class="mcd-ch3">1. Most of your pain is a second arrow — and you fired that one yourself.</div>' +
        '<div class="mcd-cp">In the Sallatha Sutta (SN 36.6, <em>"The Dart"</em>), the Buddha describes someone struck by an arrow, who is then struck by a <em>second</em> arrow in the same wound. The first arrow is the actual painful thing: a loss, an uncertainty, an unpleasant feeling. Life delivers that one, and often you can\'t avoid it. The second arrow is everything the mind piles on top — the resisting, the dread, the rehearsing of disaster.</div>' +
        '<div class="mcd-cp">He says the untrained person, touched by painful feeling, sorrows and laments and "falls into confusion," and so feels <em>two</em> feelings, bodily and mental. The trained person feels only the first: "one feeling — physical, not mental."</div>' +
        '<div class="mcd-cp">Worry is almost entirely the second arrow. The thing you fear (the test result, the deadline, the conversation) is the first arrow, and it has a real, finite size. The hours spent rehearsing it in your head are the second arrow — and that one is optional. The practice begins the moment you catch yourself reaching for it, and choose not to.</div>' +
        '<div class="mcd-ch3">2. Worry has no home in the present. It lives in a past that\'s gone and a future that hasn\'t come.</div>' +
        '<div class="mcd-cp">This is the Bhaddekaratta Sutta (MN 131, <em>"One Fine Night"</em>). The core verse:</div>' +
        '<div class="mcd-cverse">Don\'t run back to the past,<br>don\'t anticipate the future.<br>What\'s past is left behind,<br>the future has not arrived;<br>and any present phenomenon<br>you clearly discern in every case.</div>' +
        '<div class="mcd-cp">Notice the structure of worry: it is always either <em>re-chewing</em> something already finished, or <em>pre-living</em> something not yet real. The Buddha\'s point is that neither actually exists right now — they exist only as thoughts the mind is generating. The cure is not to suppress them but to keep clearly seeing the one thing that is real: this present moment.</div>' +
        '<div class="mcd-ch3">The practical anchor — how you actually come back.</div>' +
        '<div class="mcd-cp">Seeing the present is a skill, and the standard training tool is mindfulness of breathing (<em>ānāpānasati</em>), set out in the Ānāpānasati Sutta (MN 118) and the Satipaṭṭhāna Sutta (MN 10, the foundational text on mindfulness). The instruction is plain: when worry pulls the mind into the future, bring attention to the physical sensation of breathing — a long breath known as long, a short breath known as short. You don\'t control it; you just <em>know</em> it. Each time the mind bolts back to the story, you notice, and gently return to the breath. Not once — thousands of times. That repetition <em>is</em> the practice. You\'re not trying to win an argument with the worry; you\'re training the mind to release it and rest where it\'s safe.</div>' +
        '<div class="mcd-ch3">One honest note.</div>' +
        '<div class="mcd-cp">This reframes worry and slowly retrains the mind, but it\'s a practice, not a switch — it works through repetition over time, not a single insight. And if your worry is severe enough to feel constant and overwhelming, the Dhamma sits well <em>alongside</em> professional support, not in place of it; the two don\'t conflict.</div>' +
        '<div class="mcd-cp" style="margin-bottom:6px">If it would help, I can open either sutta in a reader panel right here so you can sit with the full passage.</div>' +
        '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn36.6" target="_blank" rel="noopener">SN 36.6</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn131" target="_blank" rel="noopener">MN 131</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn118" target="_blank" rel="noopener">MN 118</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn10" target="_blank" rel="noopener">MN 10</a></div>',
      answer: ''
      },
      {
        question: 'The First Noble Truth says life is suffering — does the Buddha mean existence is inherently painful?',
        toolName: 'search_hybrid',
        toolArgs: 'query="dukkha meaning · first noble truth · pessimism"',
        statuses: ['scanning…', 'matching vectors…', '4 passages found'],
        toolDur: 3.8,
        dur: 30,
        type: 'chat',
        html:
          '<div class="mcd-cp"><strong>Short answer: no</strong> — not "painful" in the sense that every moment hurts. The phrase "life is suffering" is a loose translation that creates exactly this misunderstanding. The Buddha\'s actual claim is narrower: anything you grasp at for <em>lasting</em> happiness can\'t give it, because it doesn\'t last. That gap is what he\'s pointing to.</div>' +
          '<div class="mcd-ch3">1. "Suffering" is a thin translation of <em>dukkha</em></div>' +
          '<div class="mcd-cp">The First Noble Truth uses the Pāli word <em>dukkha</em>. "Suffering" only captures one slice of it. <em>Dukkha</em> also covers stress, dissatisfaction, and unreliability — the sense that something can\'t be leaned on.</div>' +
          '<div class="mcd-cp">In the Buddha\'s first discourse (Dhammacakkappavattana Sutta, SN 56.11) he does <em>not</em> say "all life is dukkha." He lists specific things — birth, aging, sickness, death — and then sums up: the five grasping-aggregates are dukkha. The key word is <em>grasping</em> (Pāli <em>upādāna</em>). The problem isn\'t that these exist. The problem is grasping at them — treating impermanent things as if they could be a permanent source of satisfaction.</div>' +
          '<div class="mcd-ch3">2. The three kinds of <em>dukkha</em> — only one is actual pain</div>' +
          '<div class="mcd-cp">Sāriputta (Saṅgītisutta, DN 33) breaks <em>dukkha</em> into three kinds:</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr"><span>Pāli</span><span>Meaning</span><span>Example</span></div>' +
            '<div class="mcd-trow"><span class="mcd-tpali">dukkha-dukkhatā</span><span>ordinary pain</span><span>a headache, grief</span></div>' +
            '<div class="mcd-trow"><span class="mcd-tpali">vipariṇāma-dukkhatā</span><span>ache of change</span><span>a good moment ending</span></div>' +
            '<div class="mcd-trow"><span class="mcd-tpali">saṅkhāra-dukkhatā</span><span>unsatisfactoriness in all conditioned things</span><span>even calm pleasure can\'t fully last</span></div>' +
          '</div>' +
          '<div class="mcd-cp">Only the first is "pain." Even a genuinely pleasant experience counts as <em>dukkha</em> — not because it feels bad, but because it can\'t last. <em>"Inherently unable to give lasting satisfaction"</em> is closer than "inherently painful."</div>' +
          '<div class="mcd-ch3">3. Why this is a diagnosis, not a verdict on existence</div>' +
          '<div class="mcd-cp">The Buddha says the First Noble Truth is to be <em>fully understood</em> — framed like a doctor\'s diagnosis, not a sentence. The Four Noble Truths follow a medical shape: symptom (<em>dukkha</em>) → cause (craving, <em>taṇhā</em>) → it can end (<em>nirodha</em>) → the treatment (the eightfold path).</div>' +
          '<div class="mcd-cp">There\'s also a Third Noble Truth: the <em>cessation</em> of dukkha (SN 56.11:4.6). If it can end, it isn\'t a permanent feature of existence. And <em>nibbāna</em> (the unconditioned, the goal) is explicitly <em>not</em> dukkha. Existence is not a closed trap.</div>' +
          '<div class="mcd-ch3">So, precisely</div>' +
          '<div class="mcd-cp">The claim is: <em>as long as you reach for impermanent things to give you lasting peace, there\'s a built-in mismatch — they can\'t deliver it — and that mismatch is dukkha.</em> His point is that the mismatch can be ended by changing your relationship to those things, not by escaping existence.</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">This is also why you\'ll often see <em>dukkha</em> left untranslated — to keep its full meaning and sidestep the "life is misery" reading you\'ve correctly questioned.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn56.11" target="_blank" rel="noopener">SN 56.11</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dn33" target="_blank" rel="noopener">DN 33</a></div>',
        answer: ''
      },
      {
        question: 'Is Buddhism pessimistic? What does the Buddha say about joy, pleasure, and happiness?',
        toolName: 'search_hybrid',
        toolArgs: 'query="sukha happiness · pessimism · joy nibbāna"',
        statuses: ['scanning…', 'matching vectors…', '5 passages found'],
        toolDur: 3.8,
        dur: 32,
        type: 'chat',
        html:
          '<div class="mcd-cp"><strong>Short answer: no</strong> — calling Buddhism pessimistic is largely a 19th-century Western misreading (Schopenhauer-flavored). The Buddha taught a great deal about happiness, sorted it into types, and explicitly said some types <em>should</em> be actively pursued. What he refused to do was pretend that fragile happiness is reliable happiness.</div>' +
          '<div class="mcd-ch3">Why "pessimistic" misses the point</div>' +
          '<div class="mcd-cp">The charge usually rests on the First Noble Truth: <em>dukkha</em>. But <em>dukkha</em> doesn\'t mean "everything is pain." It\'s closer to <em>unsatisfactoriness</em> — conditioned things can\'t give lasting contentment because they keep changing. Pleasant things are real; they just don\'t stay, and clinging to what won\'t stay is where the ache comes from.</div>' +
          '<div class="mcd-cp">The Buddha framed his whole teaching like a physician\'s: diagnosis (there is dukkha), cause (<em>taṇhā</em> — craving), prognosis (it can end), prescription (the eightfold path). A doctor who names your illness isn\'t a pessimist. The entire structure is engineered to <em>end</em> suffering — the opposite of resignation.</div>' +
          '<div class="mcd-cp">He was also explicit that punishing yourself is not the path. In his very first discourse he rejected two dead ends — chasing sense pleasure (<em>kāmasukhallikānuyoga</em>) and self-torture (<em>attakilamathānuyoga</em>) — and called his way the Middle Way (SN 56.11). Buddhism rejects life-denial as one of its two named errors.</div>' +
          '<div class="mcd-ch3">What the Buddha actually says about joy and happiness</div>' +
          '<div class="mcd-cp">Quite a lot — there is even a whole chapter of the Dhammapada titled <em>Sukhavagga</em>, "Happiness" (Dhp 197–208). The key move is that he never treats "pleasure" as a single thing. He grades it by whether it holds up:</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr"><span>Kind of happiness (<em>sukha</em>)</span><span>What it is</span><span>The Buddha\'s stance</span></div>' +
            '<div class="mcd-trow"><span class="mcd-tpali">Sense pleasure (<em>kāmasukha</em>)</span><span>Pleasure from sights, food, sex, comfort</span><span>Real, but unreliable — feeds craving. Fine for laypeople, not where lasting peace lives</span></div>' +
            '<div class="mcd-trow"><span class="mcd-tpali">Householder happiness</span><span>Ordinary goods of a well-lived lay life (AN 4.62)</span><span>Explicitly praised and legitimate</span></div>' +
            '<div class="mcd-trow"><span class="mcd-tpali">Happiness of renunciation &amp; meditation</span><span>Joy of a calm, uncluttered mind (MN 66)</span><span>Should be actively cultivated</span></div>' +
            '<div class="mcd-trow"><span class="mcd-tpali">Nibbāna</span><span>Peace of a mind free of craving (Dhp 204)</span><span>The highest happiness of all</span></div>' +
          '</div>' +
          '<div class="mcd-cp">To the layman Anāthapiṇḍika, the Buddha named four happinesses a householder can rightly enjoy: honestly-earned wealth (<em>atthi-sukha</em>), using it (<em>bhoga-sukha</em>), freedom from debt (<em>ānaṇya-sukha</em>), and blameless living (<em>anavajja-sukha</em>) — AN 4.62. He ranks them, but still calls all four happiness and treats them as worth having.</div>' +
          '<div class="mcd-cp">The most decisive point: in MN 66 (Laṭukikopama Sutta) the Buddha names "the pleasure of renunciation, of seclusion, of peace, of awakening" and says this pleasure <em>should be cultivated and developed, and should not be feared.</em> Joy is on the road, not against it. The rapture (<em>pīti</em>) and bliss (<em>sukha</em>) of meditative absorption (<em>jhāna</em>) are actual path factors (SN 45.8).</div>' +
          '<div class="mcd-cp">At the top sits <em>nibbāna</em>, described flatly as the supreme happiness: <em>nibbānaṃ paramaṃ sukhaṃ</em> (Dhp 204).</div>' +
          '<div class="mcd-ch3">So the through-line</div>' +
          '<div class="mcd-cp">The Buddha isn\'t anti-happiness — he\'s re-educating you about <em>which</em> happiness holds up. Sense pleasure is like borrowing: it feels good now, but the bill arrives when the pleasant thing ends. The happiness of a clear, peaceful, undefiled mind doesn\'t depend on acquiring or keeping anything, so nothing can take it away. Diagnosing the first honestly, and pointing to the second, is realism — not pessimism.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn56.11" target="_blank" rel="noopener">SN 56.11</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/an4.62" target="_blank" rel="noopener">AN 4.62</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn66" target="_blank" rel="noopener">MN 66</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn45.8" target="_blank" rel="noopener">SN 45.8</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dhp197-208" target="_blank" rel="noopener">Dhp 204</a></div>',
        answer: ''
      }
      ]  // end search_hybrid.scenarios
    },
    {
      tab: 'survey_corpus',
      scenarios: [{
        question: 'What places are mentioned in the Buddhist Canon? Give their names and how often they appear.',
        toolName: 'survey_corpus',
        toolArgs: '"sāvatthī" + 12 major place names, match_scope="stem"',
        statuses: ['surveying cities…', 'cross-checking regions…', '13 places · counts complete'],
        toolDur: 4.1,
        dur: 40,
        type: 'chat',
        html:
          '<div class="mcd-cp">Yes — and the geography of the Canon is <strong>heavily skewed toward one city</strong>. <em>Sāvatthī</em> appears in 1,311 distinct texts, nearly 3½× more than its nearest rival. The reason is as much structural as biographical.</div>' +
          '<div class="mcd-ch3">Major cities (segments / distinct texts)</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span>City</span><span>Segs</span><span>Texts</span><span>What it is</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Sāvatthī ★</span><span>2,014</span><span>1,311</span><span>Capital of Kosala — home of Jetavana grove</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Jetavana</span><span>687</span><span>600</span><span>Anāthapiṇḍika\'s monastery at Sāvatthī</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Rājagaha</span><span>604</span><span>228</span><span>Capital of Magadha; Veḷuvana monastery</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Vesālī</span><span>347</span><span>98</span><span>Licchavi capital; central to the last journey</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Bārāṇasī</span><span>184</span><span>96</span><span>Near Isipatana — the Deer Park; first sermon</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Kapilavatthu</span><span>125</span><span>63</span><span>The Sakyan capital — the Buddha\'s hometown</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Kusinārā</span><span>67</span><span>26</span><span>Site of the parinibbāna — almost entirely in DN 16</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Isipatana</span><span>62</span><span>42</span><span>Deer Park near Bārāṇasī; the first discourse</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">Why Sāvatthī dominates so completely</div>' +
          '<div class="mcd-cp">Most suttas in the Saṁyutta and Aṅguttara Nikāyas open with a stock setting line — <em>“At one time the Blessed One was dwelling near Sāvatthī, in Jeta\'s Grove, Anāthapiṇḍika\'s monastery.”</em> This <em>nidāna</em> formula is baked into thousands of suttas as their structural template — so Sāvatthī\'s count reflects its role as the default setting, not only the suttas actually set there.</div>' +
          '<div class="mcd-ch3">Kingdoms and regions</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span>Region</span><span>Segs</span><span>Texts</span><span>Note</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Kosala</span><span>≈ 500</span><span>≈ 170</span><span>Northern kingdom; King Pasenadi (includes homonym <em>kosalla</em>)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Magadha</span><span>452</span><span>98</span><span>Eastern kingdom; Kings Bimbisāra and Ajātasattu</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Himavā (Himalayas)</span><span>188</span><span>122</span><span>Mostly in similes and verse — not a narrative setting</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.8fr 0.7fr 2fr"><span class="mcd-tpali">Uruvelā</span><span>≈ 27</span><span>24</span><span>Where the Buddha attained awakening — stem 134 is mostly Uruvela-Kassapa</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">The canon\'s own list — the six great cities (DN 16)</div>' +
          '<div class="mcd-cp">In DN 16, Ānanda protests the Buddha should not die in “a little town” like Kusinārā, and recites the six prestigious cities: <em>Campā, Rājagaha, Sāvatthī, Sāketa, Kosambī, Bārāṇasī.</em> Kusinārā is conspicuously absent from this prestige list — making the choice of it as the death site all the more pointed.</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">Counts are lexical — segments where the name appears. A place mentioned once in a pivotal sutta (Uruvelā in MN 26, the awakening) ranks far below cities repeated in thousands of opening formulas.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dn16" target="_blank" rel="noopener">DN 16</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn26" target="_blank" rel="noopener">MN 26</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn3.1" target="_blank" rel="noopener">SN 3.1</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn56.11" target="_blank" rel="noopener">SN 56.11</a></div>',
        answer: ''
      },
      {
        question: 'How often does "dukkha" appear across the three Piṭakas combined?',
        toolName: 'survey_corpus',
        toolArgs: '"dukkha", match_scope="stem"',
        statuses: ['counting segments…', 'tallying pitakas…', '7,836 segments found'],
        toolDur: 3.2,
        dur: 32,
        type: 'chat',
        html:
          '<div class="mcd-cp">Short answer: <strong>it depends on what you count</strong> — the two reasonable readings differ by roughly 12×. Both are from this corpus (SuttaCentral <em>bilara-data</em>, Pāli text), flagged complete with nothing dropped.</div>' +
          '<div class="mcd-ch3">Key caveat: segments, not tokens</div>' +
          '<div class="mcd-cp">The tool counts <em>segments</em> (canonical lines) containing the term, not raw word tokens. A single line like <em>"Jātipi dukkhā, jarāpi dukkhā, maraṇampi dukkhaṁ…"</em> (DN 22) may contain the word many times but counts as <strong>one segment</strong>. So this is "how many lines mention it" — the closest available proxy.</div>' +
          '<div class="mcd-ch3">The two readings</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.9fr 0.7fr 0.8fr 1.1fr 1fr"><span>Scope</span><span>Total</span><span>Sutta</span><span>Abhidhamma</span><span>Distinct suttas</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.9fr 0.7fr 0.8fr 1.1fr 1fr"><span class="mcd-tpali">exact "dukkha" (nominative only)</span><span>617</span><span>529</span><span>59</span><span>235</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.9fr 0.7fr 0.8fr 1.1fr 1fr"><span class="mcd-tpali">stem dukkha- (all inflections + compounds)</span><span>7,836</span><span>5,346</span><span>2,314</span><span>1,377</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">Why neither number is exactly right</div>' +
          '<div class="mcd-cp"><strong>617 undercounts</strong> — it\'s a literal string match, missing common inflections like <em>dukkhaṁ</em> and <em>dukkhassa</em>. It captures basically the nominative forms only.</div>' +
          '<div class="mcd-cp"><strong>7,836 overcounts</strong> — the stem sweeps in compounds: <em>dukkhanirodha</em> (cessation of suffering), <em>dukkhasamudaya</em> (origin), <em>dukkhasacca</em> (the truth of suffering). Those are arguably distinct technical terms, not bare "dukkha."</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">The honest count — all inflections but excluding compounds — sits between the two. The tool doesn\'t isolate it directly. Either way, <em>dukkha</em> touches roughly half the entire canon by stem.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dn22" target="_blank" rel="noopener">DN 22</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn56.11" target="_blank" rel="noopener">SN 56.11</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dn33" target="_blank" rel="noopener">DN 33</a></div>',
        answer: ''
      },
      {
        question: 'Which appears more often in the Canon — "sati" (mindfulness) or "paññā" (wisdom)?',
        toolName: 'survey_corpus',
        toolArgs: '"sati" vs "paññā", match_scope="stem"',
        statuses: ['surveying sati…', 'surveying paññā…', '4 runs · forms audited'],
        toolDur: 3.8,
        dur: 34,
        type: 'chat',
        html:
          '<div class="mcd-cp"><strong>Short answer: basically a tie on the bare word</strong> — and the "wisdom wins" result from a naive search is mostly a measurement artifact. The exhaustive survey reveals a different homonym trap on each side.</div>' +
          '<div class="mcd-ch3">What four survey runs return</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:2fr 1.4fr 1.4fr"><span>Method</span><span>sati (mindfulness)</span><span>paññā (wisdom)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 1.4fr 1.4fr"><span class="mcd-tpali">bare word (exact)</span><span>1,432 · 385 suttas</span><span>1,446 · 230 suttas</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 1.4fr 1.4fr"><span style="padding-left:14px;color:var(--d-dim)">↳ Sutta Piṭaka</span><span>1,207</span><span>903</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 1.4fr 1.4fr"><span style="padding-left:14px;color:var(--d-dim)">↳ Abhidhamma</span><span>181</span><span style="color:var(--d-acc)">531 ← ranking flips</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 1.4fr 1.4fr"><span class="mcd-tpali">stem (inflections + compounds)</span><span>3,752 · 961 suttas</span><span>8,461 · 1,508 suttas</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">Two homonym traps — why the raw numbers lie</div>' +
          '<div class="mcd-cp"><strong>sati\'s 1,432 is inflated.</strong> A large share of bare hits are the locative participle of <em>atthi</em> ("when there is") — the dependent-origination formula <em>imasmiṁ sati idaṁ hoti</em> ("when this exists, this comes to be") appears constantly. Same spelling, unrelated word. Genuine mindfulness-sati is materially below 1,432.</div>' +
          '<div class="mcd-cp"><strong>paññā\'s stem 8,461 is wrecked.</strong> Four false-friend families dominate: <em>paññatti / paññāpeti</em> ("concept / to declare"), <em>pannarasa</em> (the number <em>fifteen</em> — in every Vinaya observance-day recitation), <em>paṇṇa</em> (leaf, as in <em>paṇṇasālā</em> = leaf hut), and <em>panna</em> (laid down — the arahant epithet <em>pannabhāra</em>).</div>' +
          '<div class="mcd-ch3">The honest bottom line</div>' +
          '<div class="mcd-cp">Bare word: <strong>dead heat</strong>, slight real edge to paññā once sati\'s participle is discounted. Most interesting finding: <strong>the answer depends on which collection you ask.</strong> In the Abhidhamma, paññā clearly leads (531 vs 181) — wisdom is a discrete <em>cetasika</em> dissected exhaustively. In the Suttas, bare sati leads (1,207 vs 903), partly due to the participle artifact.</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">A definitive ranking would require de-contaminating both stem lists form by form — the tool returns every surface form for exactly this purpose — but it cannot collapse to a single headline number.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn38" target="_blank" rel="noopener">MN 38</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn12.23" target="_blank" rel="noopener">SN 12.23</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dn22" target="_blank" rel="noopener">DN 22</a></div>',
        answer: ''
      }]
    },
    {
      tab: 'get_word_definition',
      scenarios: [{
        question: 'What does the word "nibbāna" mean? Show the dictionary definition.',
        toolName: 'get_word_definition',
        toolArgs: '"nibbāna"',
        statuses: ['looking up nibbāna…', 'PTS Dictionary · Payutto found'],
        toolDur: 2.3,
        dur: 32,
        type: 'chat',
        html:
          '<div class="mcd-cp"><strong>Nibbāna</strong> (Sanskrit: <em>nirvāṇa</em>) — literally "extinguishing / going out," as of a fire or lamp. Not annihilation. Not a metaphysical place.</div>' +
          '<div class="mcd-ch3">Etymology</div>' +
          '<div class="mcd-cp">The form is <em>nir + √vā</em> ("to blow out") — but the Pāli tradition also reads it as <em>nis + vana</em>, "going out of <em>vana</em>" (craving). The governing image: a fire going <strong>out for lack of fuel</strong>, not blown out (blowing would feed it).</div>' +
          '<div class="mcd-ch3">The four dictionary senses (PTS, in order)</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.5fr 1fr 3fr"><span>#</span><span>Sense</span><span>Meaning</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.5fr 1fr 3fr"><span>1</span><span class="mcd-tpali">Literal</span><span>The going out of a lamp or fire — the everyday meaning.</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.5fr 1fr 3fr"><span>2</span><span class="mcd-tpali">Health</span><span>Bodily well-being; the passing of feverishness or restlessness.</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.5fr 1fr 3fr"><span style="color:var(--d-acc)">3</span><span class="mcd-tpali" style="color:var(--d-acc)!important">Buddhist ★</span><span>Dying out of the threefold fire — <em>rāga</em> (passion), <em>dosa</em> (ill-will), <em>moha</em> (delusion).</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.5fr 1fr 3fr"><span>4</span><span class="mcd-tpali">Spiritual</span><span>Security, emancipation, peace — the highest happiness.</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">The core point</div>' +
          '<div class="mcd-cp">Nibbāna is treated as an <em>ethical/experiential state</em> — reachable in this very life through the Noble Eightfold Path, not a metaphysical "place," and not annihilation. The canon defines it directly:</div>' +
          '<div class="mcd-cverse">"The wearing away of lust, of hatred, of delusion —<br>this is called nibbāna."<br><span style="color:var(--d-dim);font-size:11px">— SN 38.1 (Nibbānapañha)</span></div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">This is why the Dhammapada calls it the supreme happiness: <em>nibbānaṃ paramaṃ sukhaṃ</em> (Dhp 203).</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn38.1" target="_blank" rel="noopener">SN 38.1</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dhp197-208" target="_blank" rel="noopener">Dhp 203</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn35.95" target="_blank" rel="noopener">SN 35.95</a></div>',
        answer: ''
      },
      {
        question: 'What does the word "kamma" mean? Show the dictionary definition.',
        toolName: 'get_word_definition',
        toolArgs: '"kamma"',
        statuses: ['looking up kamma…', 'PTS Dictionary · Payutto found'],
        toolDur: 2.3,
        dur: 34,
        type: 'chat',
        html:
          '<div class="mcd-cp"><strong>Kamma</strong> (Sanskrit <em>karman</em> — source of English "karma") literally means "deed, action, work." From <em>karoti</em> ("to do / to make") — at root, kamma is simply <em>what you do</em>.</div>' +
          '<div class="mcd-ch3">Two layers of meaning (PTS Dictionary)</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1fr 3.5fr"><span>Sense</span><span>What it means</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1fr 3.5fr"><span class="mcd-tpali">Plain</span><span>Deed, action, work — also "occupation" and formal monastic proceedings (<em>saṅghakamma</em>).</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1fr 3.5fr"><span class="mcd-tpali">Doctrinal</span><span>Intentional deed (good or bad) → repeated deed forming character → deed as accumulated moral consequence.</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">Three channels — the doors of kamma</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.2fr 1fr 2.5fr"><span>Door</span><span>Pāli</span><span>What it covers</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.2fr 1fr 2.5fr"><span class="mcd-tpali">Body</span><span><em>kāya</em></span><span>Physical acts — how you move and act</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.2fr 1fr 2.5fr"><span class="mcd-tpali">Speech</span><span><em>vacī</em></span><span>Verbal acts — what you say</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.2fr 1fr 2.5fr"><span class="mcd-tpali">Mind</span><span><em>mano</em></span><span>Mental acts — thoughts and intentions</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">The decisive clarification — kamma = intention</div>' +
          '<div class="mcd-cp">The Canon\'s own definition goes further than any dictionary: kamma is not just any action, but <strong>intentional</strong> action (<em>cetanā</em>):</div>' +
          '<div class="mcd-cverse">"It is intention, monks, that I call kamma. Having intended, one acts through body, speech, and mind."<br><span style="color:var(--d-dim);font-size:11px">— AN 6.63 (Nibbedhika Sutta)</span></div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">An unintended act carries no kamma-weight. The moral quality of an act depends on the <em>state of mind</em> behind it — not the outcome alone. This is why intention is also the heart of the saṅkhāra-khandha (the volitional aggregate).</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/an6.63" target="_blank" rel="noopener">AN 6.63</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn135" target="_blank" rel="noopener">MN 135</a></div>',
        answer: ''
      },
      {
        question: 'What does the word "saṅkhāra" mean? Show the dictionary definition.',
        toolName: 'get_word_definition',
        toolArgs: '"saṅkhāra"',
        statuses: ['looking up saṅkhāra…', 'PTS Dictionary found · 4 senses'],
        toolDur: 2.5,
        dur: 40,
        type: 'chat',
        html:
          '<div class="mcd-cp">The PTS dictionary calls <em>saṅkhāra</em> <strong>"one of the most difficult terms in Buddhist metaphysics"</strong> — no single English word can translate it. Context determines which meaning applies.</div>' +
          '<div class="mcd-ch3">Etymology — the root gives the key</div>' +
          '<div class="mcd-cp"><em>saṁ</em> ("together") + root <em>kṛ</em> ("to make / to do") — literally "putting-together." Two sides at once: <em>passive</em> — that which has been put together (anything conditioned); <em>active</em> — the force doing the putting-together (will, volition). The one thread: <strong>things made up by pre-existing causes.</strong></div>' +
          '<div class="mcd-ch3">Four main senses</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.5fr 1.4fr 3fr"><span>#</span><span>Context</span><span>Meaning</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.5fr 1.4fr 3fr"><span>1</span><span class="mcd-tpali">All conditioned things</span><span><em>sabbe saṅkhārā</em> — everything assembled by causes. Nibbāna alone is <em>asaṅkhata</em> (unconditioned).</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.5fr 1.4fr 3fr"><span>2</span><span class="mcd-tpali">4th aggregate</span><span>Volitional/mental formations — bundle of mental factors with <em>cetanā</em> at the core. Sujato translates: "choices."</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.5fr 1.4fr 3fr"><span>3</span><span class="mcd-tpali">Dependent origination</span><span>Kamma-driven fabrications fuelled by ignorance — 2nd link: <em>avijjā-paccayā saṅkhārā</em>.</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.5fr 1.4fr 3fr"><span>4</span><span class="mcd-tpali">Three specific types</span><span><em>kāya-saṅkhāra</em> = breath · <em>vacī-saṅkhāra</em> = applied thought · <em>citta-saṅkhāra</em> = feeling + perception.</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">The most famous use — sense 1</div>' +
          '<div class="mcd-cverse">"<em>Aniccā vata saṅkhārā</em> —<br>Conditioned things are impermanent;<br>it is their nature to arise and pass away."<br><span style="color:var(--d-dim);font-size:11px">— DN 16 (at the moment of parinibbāna)</span></div>' +
          '<div class="mcd-ch3">Canonical definition of sense 2</div>' +
          '<div class="mcd-cverse">"Why are they called volitional formations?<br>Because they construct the conditioned — that is why."<br><span style="color:var(--d-dim);font-size:11px">— SN 22.79 (Khajjanīya Sutta)</span></div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">Common translations: <em>formations, volitional formations, mental formations, choices (Sujato), fabrications, constructions, kamma-formations.</em> None is fully adequate — context determines which fits.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn22.79" target="_blank" rel="noopener">SN 22.79</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dn16" target="_blank" rel="noopener">DN 16</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn12.2" target="_blank" rel="noopener">SN 12.2</a></div>',
        answer: ''
      }]
    },
    {
      tab: 'compare_translations',
      scenarios: [{
        question: 'Compare translations of Dhammapada verse 1 (Dhp 1) — show Pāli and English side by side.',
        toolName: 'compare_translations',
        toolArgs: '"dhp1:1"',
        statuses: ['fetching editions…', 'Pāli + Sujato aligned'],
        toolDur: 2.4,
        dur: 36,
        type: 'chat',
        html:
          '<div class="mcd-cp"><strong>Dhp 1</strong> — opening verse of the Dhammapada (<em>Yamakavagga</em>, "Pairs"). The database holds one verified English edition: Bhikkhu Sujato. His key choice is unusual: <em>mano</em> → "intention" rather than "mind" — tying the verse directly to the law of kamma.</div>' +
          '<div class="mcd-ch3">Pāli alongside Sujato (verified)</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:2fr 3fr"><span>Pāli</span><span>Sujato (EN)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">Manopubbaṅgamā dhammā,</span><span>Intention shapes experiences;</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">manoseṭṭhā manomayā;</span><span>intention is first, they\'re made by intention.</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">Manasā ce paduṭṭhena,</span><span>If with corrupt intent</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">bhāsati vā karoti vā;</span><span>you speak or act,</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">Tato naṁ dukkhamanveti,</span><span>suffering follows you,</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">cakkaṁva vahato padaṁ.</span><span>like a wheel, the ox\'s foot.</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">How major translators diverge</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.6fr 0.9fr 1fr 2.2fr"><span>Translator</span><span><em>mano</em></span><span><em>dhammā</em></span><span>Flavor</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.6fr 0.9fr 1fr 2.2fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Sujato (CC0) ★</span><span>intention</span><span>experiences</span><span>Reads <em>mano</em> through <em>cetanā</em> — kamma in two lines</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.6fr 0.9fr 1fr 2.2fr"><span class="mcd-tpali">Buddharakkhita (BPS)</span><span>mind</span><span>mental states</span><span>Literal, traditional</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.6fr 0.9fr 1fr 2.2fr"><span class="mcd-tpali">Ṭhānissaro Bhikkhu</span><span>heart</span><span>phenomena</span><span>"Heart" captures <em>mano</em> as seat of feeling and will</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.6fr 0.9fr 1fr 2.2fr"><span class="mcd-tpali">Müller (1881)</span><span>thought(s)</span><span>"all that we are"</span><span>Famous loose paraphrase — readable but not precise</span></div>' +
          '</div>' +
          '<div class="mcd-cp"><em>cakkaṁva vahato padaṁ</em> — "as the wheel [follows] the foot of the ox drawing the cart." Most translators spell out the cart so the image of suffering <em>trailing</em> the deed is unmistakable. Sujato compresses it hard.</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">Sujato\'s "intention" choice is deliberate: <em>kamma = cetanā</em> (AN 6.63), so this verse is literally the law of kamma — intention → deed → result.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dhp1-20" target="_blank" rel="noopener">Dhp 1–20</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/an6.63" target="_blank" rel="noopener">AN 6.63</a></div>',
        answer: ''
      },
      {
        question: 'I keep seeing different English translations of the Satipaṭṭhāna Sutta opening\nsome say "direct path," others say "one-way path." Can you show me the Pāli\noriginal alongside an English translation?',
        toolName: 'compare_translations',
        toolArgs: '"mn10:2.1"',
        statuses: ['fetching MN 10…', 'Pāli + Sujato aligned'],
        toolDur: 2.6,
        dur: 38,
        type: 'chat',
        html:
          '<div class="mcd-cp">Three camps exist — "direct path," "one-way path," and Sujato\'s "path to convergence." Here is the verified opening, then what each choice means.</div>' +
          '<div class="mcd-ch3">The Pāli opening — clause by clause (verified, mn10:2.1)</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:2fr 3fr"><span>Pāli</span><span>Sujato (EN)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">Ekāyano ayaṁ … maggo … cattāro satipaṭṭhānā</span><span>the four kinds of mindfulness meditation are the <strong>path to convergence</strong></span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">sattānaṁ visuddhiyā</span><span>to purify sentient beings</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">sokaparidevānaṁ samatikkamāya</span><span>to get past sorrow and crying</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">dukkhadomanassānaṁ atthaṅgamāya</span><span>to make an end of pain and sadness</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">ñāyassa adhigamāya</span><span>to discover the system</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2fr 3fr"><span class="mcd-tpali">nibbānassa sacchikiriyāya</span><span>to realize extinguishment (nibbāna)</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">Four renderings of <em>ekāyano maggo</em></div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.8fr 1.5fr 2.5fr"><span>Rendering</span><span>Associated with</span><span>Reading behind it</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.5fr 2.5fr"><span class="mcd-tpali">"the only path"</span><span>Nyanaponika Thera</span><span>eka = one and only; no other way works</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.5fr 2.5fr"><span class="mcd-tpali">"the direct path"</span><span>Bhikkhu Bodhi; Anālayo</span><span>goes straight to the one goal</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.5fr 2.5fr"><span class="mcd-tpali">"the one-way path"</span><span>various</span><span>runs in one direction, one destination</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.5fr 2.5fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">"path to convergence" ★</span><span>Sujato</span><span>everything in it converges on nibbāna</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">The decisive evidence — MN 12</div>' +
          '<div class="mcd-cp">The same word <em>ekāyanena maggena</em> appears in MN 12 for paths leading to a pit of coals, a sewer, a lotus pond, and a stilt house. Since the destinations include terrible ones, <em>ekāyana</em> cannot mean "the one right way." It means <strong>a path going to one specific destination</strong>.</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">"Direct," "one-way," and "convergence" all describe the same thing: a path running toward one goal (nibbāna). The older "the only way" reads in an exclusivity the Pāli doesn\'t carry.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn10" target="_blank" rel="noopener">MN 10</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dn22" target="_blank" rel="noopener">DN 22</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn12" target="_blank" rel="noopener">MN 12</a></div>',
        answer: ''
      },
      {
        question: 'Compare translations of the Buddha\'s last words Pāli and France, Thai, Japanese side by side.',
        toolName: 'compare_translations',
        toolArgs: '"dn16:6.7.3", languages=["pali","en","fr","th","ja"]',
        statuses: ['fetching DN 16…', 'Pāli + Sujato + 3 languages'],
        toolDur: 3.1,
        dur: 36,
        type: 'chat',
        html:
          '<div class="mcd-cp">The Buddha\'s final words come at the moment of parinibbāna in DN 16:6.7. The verified database holds Pāli + Sujato\'s English. The three additional languages are faithful translations from the Pāli.</div>' +
          '<div class="mcd-cverse">"<em>Vayadhammā saṅkhārā, appamādena sampādetha.</em>"<br><span style="color:var(--d-dim);font-size:11px">— DN 16:6.7.3 — "These were the Realized One\'s last words."</span></div>' +
          '<div class="mcd-ch3">Five languages side by side</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.8fr 4fr"><span>Language</span><span>Translation</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.8fr 4fr"><span class="mcd-tpali">Pāli</span><span style="font-style:italic">Vayadhammā saṅkhārā, appamādena sampādetha.</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.8fr 4fr"><span class="mcd-tpali">English</span><span>"Conditions fall apart. Persist with diligence." <span style="color:var(--d-dim);font-size:11px">(Sujato, verified)</span></span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.8fr 4fr"><span class="mcd-tpali">French</span><span>« Les formations conditionnées sont sujettes à la disparition ; accomplissez votre but avec diligence. »</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.8fr 4fr"><span class="mcd-tpali">Thai</span><span>สังขารทั้งหลายมีความเสื่อมสลายไปเป็นธรรมดา เธอทั้งหลายจงยังกิจให้ถึงพร้อมด้วยความไม่ประมาทเถิด</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.8fr 4fr"><span class="mcd-tpali">Japanese</span><span>諸行は滅びゆくものである。不放逸をもって、なすべきことを成し遂げなさい。</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">Where translators diverge most — <em>sampādetha</em></div>' +
          '<div class="mcd-cp"><em>Sampādetha</em> ("bring to completion") is the richest word. Sujato\'s "persist" is lean. T.W. Rhys Davids\' 1910 rendering — <em>"Work out your salvation with diligence"</em> — supplied "salvation" as the unstated object. Thai มหาจุฬาฯ: <em>จงยังกิจให้ถึงพร้อม</em> ("bring your task to completion"), leaving the object unspecified as the Pāli does.</div>' +
          '<div class="mcd-ch3">The Japanese cultural echo</div>' +
          '<div class="mcd-cp"><em>Saṅkhārā</em> → 諸行 (<em>shogyō</em>) is the same word in <em>諸行無常</em> (<em>shogyō mujō</em>) — the opening line of the Heike Monogatari, perhaps the single most famous Buddhist phrase in Japan. The Buddha\'s dying line is that same truth turned into a final instruction: <em>because</em> conditions fall apart — <em>therefore</em> act with diligence.</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">The same Pāli verse also appears at SN 6.15 in Brahmā Sahampati\'s eulogy at the moment of parinibbāna.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dn16" target="_blank" rel="noopener">DN 16</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn6.15" target="_blank" rel="noopener">SN 6.15</a></div>',
        answer: ''
      }]
    },
    {
      tab: 'get_sutta',
      scenarios: [{
        question: 'Show me the full breath meditation instructions — the Ānāpānasati Sutta.',
        toolName: 'get_sutta',
        toolArgs: '"mn118"',
        statuses: ['fetching MN 118…', '16 steps mapped'],
        toolDur: 2.6,
        dur: 42,
        type: 'chat',
        html:
          '<div class="mcd-cp"><strong>MN 118</strong> is the only sutta where all <strong>16 steps</strong> of breath meditation appear together. The Satipaṭṭhāna discourses (MN 10 / DN 22) cover only the first four under "body contemplation." The 16 steps map onto the four foundations in four groups of four — <em>tetrads</em> — and form a chain: ānāpānasati fulfills the four satipaṭṭhāna → which fulfill the seven bojjhaṅga → which fulfill vijjā-vimutti (knowledge and liberation).</div>' +
          '<div class="mcd-cp">Steps 1–2 use <em>pajānāti</em> — you simply <strong>know</strong> the breath as it is. From step 3 onward each uses <em>sikkhati</em> — you <strong>train</strong>, deliberately cultivating that quality on both in-breath and out-breath.</div>' +
          '<div class="mcd-ch3">Tetrad 1 — Body (<em>kāya</em>)</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.3fr 2fr 3fr"><span>#</span><span>Pāli</span><span>Practice</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>1</span><span class="mcd-tpali">dīgha</span><span>Breathing in/out long — <em>know</em> it as long</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>2</span><span class="mcd-tpali">rassa</span><span>Breathing in/out short — <em>know</em> it as short</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>3</span><span class="mcd-tpali">sabbakāyapaṭisaṁvedī</span><span>Train: breathe experiencing the whole body</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>4</span><span class="mcd-tpali">passambhayaṁ kāyasaṅkhāraṁ</span><span>Train: breathe stilling the physical process</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">Tetrad 2 — Feeling (<em>vedanā</em>)</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.3fr 2fr 3fr"><span>#</span><span>Pāli</span><span>Practice</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>5</span><span class="mcd-tpali">pītipaṭisaṁvedī</span><span>Train: breathe experiencing rapture (<em>pīti</em>)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>6</span><span class="mcd-tpali">sukhapaṭisaṁvedī</span><span>Train: breathe experiencing bliss (<em>sukha</em>)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>7</span><span class="mcd-tpali">cittasaṅkhārapaṭisaṁvedī</span><span>Train: breathe experiencing the mental process</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>8</span><span class="mcd-tpali">passambhayaṁ cittasaṅkhāraṁ</span><span>Train: breathe stilling the mental process</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">Tetrad 3 — Mind (<em>citta</em>)</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.3fr 2fr 3fr"><span>#</span><span>Pāli</span><span>Practice</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>9</span><span class="mcd-tpali">cittapaṭisaṁvedī</span><span>Train: breathe experiencing the mind</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>10</span><span class="mcd-tpali">abhippamodayaṁ cittaṁ</span><span>Train: breathe gladdening the mind</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>11</span><span class="mcd-tpali">samādahaṁ cittaṁ</span><span>Train: breathe immersing the mind in <em>samādhi</em></span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>12</span><span class="mcd-tpali">vimocayaṁ cittaṁ</span><span>Train: breathe freeing the mind</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">Tetrad 4 — Principles (<em>dhamma</em>)</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.3fr 2fr 3fr"><span>#</span><span>Pāli</span><span>Practice</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>13</span><span class="mcd-tpali">aniccānupassī</span><span>Train: breathe observing impermanence (<em>anicca</em>)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>14</span><span class="mcd-tpali">virāgānupassī</span><span>Train: breathe observing fading away (<em>virāga</em>)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>15</span><span class="mcd-tpali">nirodhānupassī</span><span>Train: breathe observing cessation (<em>nirodha</em>)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.3fr 2fr 3fr"><span>16</span><span class="mcd-tpali" style="color:var(--d-acc)!important">paṭinissaggānupassī ★</span><span>Train: breathe observing letting go (<em>paṭinissagga</em>) — the final release</span></div>' +
          '</div>' +
          '<div class="mcd-cp">Three key terms: <em>kāyasaṅkhāra</em> = breath itself (the "bodily formation") — stilling it means letting it grow subtler naturally, not forcing; <em>cittasaṅkhāra</em> = perception and feeling, the activity that shapes the mind; <em>paṭinissagga</em> = relinquishment — the final movement of the whole practice, pointed toward liberation.</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">MN 118 gives the <em>map</em>, not a "how long on each step" manual. The canon deliberately leaves pacing to a teacher and one\'s own experience.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn118" target="_blank" rel="noopener">MN 118</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn10" target="_blank" rel="noopener">MN 10</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn54.1" target="_blank" rel="noopener">SN 54.1</a></div>',
        answer: ''
      },
      {
        question: 'What did the Buddha say in his very first teaching? The one he gave right after his awakening.',
        toolName: 'get_sutta',
        toolArgs: '"sn56.11"',
        statuses: ['fetching SN 56.11…', 'First Discourse loaded'],
        toolDur: 1.8,
        dur: 45,
        type: 'chat',
        html:
          '<div class="mcd-cp">The first teaching is the <strong>Dhammacakkappavattana Sutta</strong> — "Setting the Wheel of the Dhamma in Motion" (SN 56.11). Given at the deer park at Isipatana (modern Sarnath) to the five ascetics who had practiced alongside him before his awakening.</div>' +
          '<div class="mcd-ch3">Two extremes to avoid</div>' +
          '<div class="mcd-cp">One "gone forth" should avoid two paths: <em>kāmasukhallikānuyoga</em> (indulgence in sensual pleasure — low, crude, pointless) and <em>attakilamathānuyoga</em> (self-mortification — painful and equally pointless). This was pointed — his five listeners were committed ascetics betting on self-mortification.</div>' +
          '<div class="mcd-ch3">The Middle Way — Noble Eightfold Path</div>' +
          '<div class="mcd-cp">The <em>majjhimā paṭipadā</em> "gives vision and knowledge, and leads to peace, direct knowledge, awakening, and extinguishment." He immediately defined it as the <em>ariyo aṭṭhaṅgiko maggo</em>:</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.4fr 1.6fr 2.5fr"><span>#</span><span>English</span><span>Pāli</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.4fr 1.6fr 2.5fr"><span>1</span><span>Right view</span><span class="mcd-tpali">sammādiṭṭhi</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.4fr 1.6fr 2.5fr"><span>2</span><span>Right intention</span><span class="mcd-tpali">sammāsaṅkappa</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.4fr 1.6fr 2.5fr"><span>3</span><span>Right speech</span><span class="mcd-tpali">sammāvācā</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.4fr 1.6fr 2.5fr"><span>4</span><span>Right action</span><span class="mcd-tpali">sammākammanta</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.4fr 1.6fr 2.5fr"><span>5</span><span>Right livelihood</span><span class="mcd-tpali">sammāājīva</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.4fr 1.6fr 2.5fr"><span>6</span><span>Right effort</span><span class="mcd-tpali">sammāvāyāma</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.4fr 1.6fr 2.5fr"><span>7</span><span>Right mindfulness</span><span class="mcd-tpali">sammāsati</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:0.4fr 1.6fr 2.5fr"><span>8</span><span>Right immersion</span><span class="mcd-tpali">sammāsamādhi</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">The Four Noble Truths with their tasks</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.3fr 2.8fr 1.2fr"><span>Noble truth</span><span>What it is</span><span>Task</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.3fr 2.8fr 1.2fr"><span class="mcd-tpali">Dukkha</span><span>Birth, aging, death, grief; the five grasping aggregates</span><span>Fully understand</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.3fr 2.8fr 1.2fr"><span class="mcd-tpali">Samudaya</span><span>Craving (<em>taṇhā</em>) — for pleasure, existence, non-existence</span><span>Give up</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.3fr 2.8fr 1.2fr"><span class="mcd-tpali">Nirodha</span><span>Complete fading away and ending of that craving</span><span>Realize</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.3fr 2.8fr 1.2fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Magga ★</span><span>The Noble Eightfold Path above</span><span>Develop</span></div>' +
          '</div>' +
          '<div class="mcd-cp">Each truth has three levels of knowledge — <em>this is</em> the truth / this truth <em>has a task</em> / that task <em>has been done</em> — giving 4 × 3 = the "three rounds and twelve aspects." Only when purified across all twelve did he declare <em>anuttara sammāsambodhi</em>.</div>' +
          '<div class="mcd-cverse">"Everything that is liable to arise is liable to cease."<br><span style="color:var(--d-dim);font-size:11px">— The <em>dhammacakkhu</em> that arose in Koṇḍañña while this was being spoken. He was thereafter called <em>Aññāsi Koṇḍañña</em> — "Koṇḍañña Who Understood."</span></div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">Everything the tradition later built — satipaṭṭhāna, breath meditation, the entire path — sits inside the <em>fourth truth</em> here. This sutta is the skeleton; the rest of the canon is the detail hung on it.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn56.11" target="_blank" rel="noopener">SN 56.11</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn56.12" target="_blank" rel="noopener">SN 56.12</a></div>',
        answer: ''
      },
      {
        question: 'What is the Fire Sermon? Show me what the Buddha actually said.',
        toolName: 'get_sutta',
        toolArgs: '"sn35.28"',
        statuses: ['fetching SN 35.28…', 'Ādittapariyāya loaded'],
        toolDur: 1.7,
        dur: 38,
        type: 'chat',
        html:
          '<div class="mcd-cp">The <strong>Ādittapariyāya Sutta</strong> ("The Burning," SN 35.28) is traditionally the Buddha\'s third major discourse — after the First Sermon and the not-self discourse. He gave it at Gayāsīsa (Gayā Head) to a thousand former fire-worshipping ascetics: the three Kassapa brothers and their followers.</div>' +
          '<div class="mcd-ch3">The thesis — "all is burning"</div>' +
          '<div class="mcd-cp"><em>Sabbaṁ, bhikkhave, ādittaṁ</em> — "Mendicants, all is burning." "All" is not a vague cosmic everything: the Buddha immediately defines it as the machinery of experience itself — each of the six senses (eye, ear, nose, tongue, body, mind), its objects, the consciousness arising at each, the contact, and the feeling born from that contact. <em>Every channel through which you experience anything</em> is on fire.</div>' +
          '<div class="mcd-ch3">Burning with what — the three fires</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1fr 4fr"><span>Fire</span><span>Meaning</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1fr 4fr"><span class="mcd-tpali">rāga</span><span>Greed / lust — grasping toward what is pleasant</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1fr 4fr"><span class="mcd-tpali">dosa</span><span>Hate / aversion — pushing away what is unpleasant</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1fr 4fr"><span class="mcd-tpali">moha</span><span>Delusion — not seeing how experience actually arises</span></div>' +
          '</div>' +
          '<div class="mcd-cp">Plus the wider blaze of <em>saṁsāra</em>: birth, aging, death, sorrow, lamentation, pain, sadness, distress.</div>' +
          '<div class="mcd-ch3">The way out</div>' +
          '<div class="mcd-cp">Seeing this clearly, the disciple grows <em>nibbidā</em> (disenchanted) → <em>virāga</em> (dispassion) → <em>vimutti</em> (release) → knowledge: "rebirth is ended, the holy life has been lived." The logic is causal, not moralistic: you don\'t <em>force</em> yourself to let go — you see clearly that everything you\'re clinging to is burning, and the grip simply releases on its own.</div>' +
          '<div class="mcd-cverse">"Seeing this, the disciple grows disenchanted with the eye, with sights, with eye-consciousness, with eye-contact, and with whatever feeling arises from eye-contact — pleasant, painful, or neutral."<br><span style="color:var(--d-dim);font-size:11px">— SN 35.28 (Ādittapariyāya Sutta)</span></div>' +
          '<div class="mcd-cp">The discourse ends with all thousand mendicants liberated while it was still being spoken — an unusually dramatic outcome even by canonical standards. The fire imagery fits the audience: <em>you tended sacred fires — here is the only fire worth putting out</em>.</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">T.S. Eliot named Part III of <em>The Waste Land</em> after this discourse and cited it in his notes — the most famous literary echo of the Fire Sermon in Western literature.</div>' +
          '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn35.28" target="_blank" rel="noopener">SN 35.28</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn35.23" target="_blank" rel="noopener">SN 35.23</a></div>',
        answer: ''
      }]
    },
    {
      tab: 'list_structure',
      scenarios: [{
        question: 'How is the Pāli Canon structured? What are the three baskets?',
        toolName: 'list_structure',
        toolArgs: '',
        statuses: ['querying…', 'Canon structure loaded'],
        toolDur: 1.5,
        dur: 28,
        type: 'chat',
        html:
          '<div class="mcd-cp">The Pāli Canon (<em>Tipiṭaka</em> — "Three Baskets") contains <strong>444,673 segments</strong> across three piṭakas, at parity with SuttaCentral bilara-data. Each basket has a different character and language coverage.</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.4fr 1.8fr 1fr 1fr 1.6fr"><span>Basket</span><span>Pāli name</span><span>Texts</span><span>Segments</span><span>Languages indexed</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.4fr 1.8fr 1fr 1fr 1.6fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Sutta Piṭaka ★</span><span class="mcd-tpali">Suttantapiṭaka</span><span>5,791 suttas</span><span>284,702</span><span>Pāli + Sujato EN</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.4fr 1.8fr 1fr 1fr 1.6fr"><span class="mcd-tpali">Abhidhamma Piṭaka</span><span class="mcd-tpali">Abhidhammapiṭaka</span><span>1,108 sections</span><span>88,414</span><span>Pāli only</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.4fr 1.8fr 1fr 1fr 1.6fr"><span class="mcd-tpali">Vinaya Piṭaka</span><span class="mcd-tpali">Vinayapiṭaka</span><span>422 texts</span><span>71,557</span><span>Pāli + Brahmali EN</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">What each basket contains</div>' +
          '<div class="mcd-cp"><strong>Sutta Piṭaka</strong> — the Buddha\'s discourses, organized into five nikāyas (DN, MN, SN, AN, KN). The working corpus for most practice and research. Sujato\'s English is the primary translation layer.</div>' +
          '<div class="mcd-cp"><strong>Abhidhamma Piṭaka</strong> — systematic philosophical analysis: 7 books that re-examine the entire teaching through an analytical lens. No English translation is indexed (bilara-data carries Pāli only for Abhidhamma).</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px"><strong>Vinaya Piṭaka</strong> — monastic discipline: rules for monks (222) and nuns (127), plus 22 chapters of procedural law (Khandhaka) and a summary compendium (Parivāra). Brahmali\'s English is indexed.</div>',
        answer: ''
      },
      {
        question: 'What are the five Nikayas? Which one has the most suttas?',
        toolName: 'list_structure',
        toolArgs: '',
        statuses: ['querying…', 'Sutta Piṭaka detail loaded'],
        toolDur: 1.5,
        dur: 38,
        type: 'chat',
        html:
          '<div class="mcd-cp">The five Nikāyas are the five divisions of the <strong>Sutta Piṭaka</strong> — the "basket of discourses," one of the three baskets of the Pāli Canon. (<em>Nikāya</em> just means <em>collection</em> or <em>group</em>.)</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.3fr 0.8fr 1.7fr 0.7fr 2.3fr"><span>Nikāya</span><span>Meaning</span><span>How organized</span><span>Suttas</span><span>Character</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.3fr 0.8fr 1.7fr 0.7fr 2.3fr"><span class="mcd-tpali">Dīgha (DN)</span><span>"Long"</span><span>34 long discourses</span><span>34</span><span>Ceremonial, narrative — the Buddha\'s last days, the Satipaṭṭhāna</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.3fr 0.8fr 1.7fr 0.7fr 2.3fr"><span class="mcd-tpali">Majjhima (MN)</span><span>"Middle-length"</span><span>152 medium discourses</span><span>152</span><span>The practice backbone — meditation, training, core doctrine</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.3fr 0.8fr 1.7fr 0.7fr 2.3fr"><span class="mcd-tpali">Saṁyutta (SN)</span><span>"Connected"</span><span>56 topic-groups (<em>saṁyuttas</em>)</span><span>~2,889</span><span>Mostly short suttas, grouped by subject</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.3fr 0.8fr 1.7fr 0.7fr 2.3fr"><span class="mcd-tpali">Aṅguttara (AN)</span><span>"Increasing by one"</span><span>11 numbered books (Ones through Elevens)</span><span>~2,344</span><span>Mostly short suttas, grouped by number (lists)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.3fr 0.8fr 1.7fr 0.7fr 2.3fr"><span class="mcd-tpali">Khuddaka (KN)</span><span>"Minor"</span><span>15–18 separate books, verse + prose</span><span>—</span><span>Dhammapada, Udāna, Sutta Nipāta, Jātaka, Theragāthā / Therīgāthā</span></div>' +
          '</div>' +
          '<div class="mcd-ch3">Which has the most suttas?</div>' +
          '<div class="mcd-cp">The two giants are <strong>Saṁyutta and Aṅguttara</strong> — each holds thousands of suttas, dwarfing Dīgha (34) and Majjhima (152). The answer flips depending on how you count:</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:2.2fr 1.2fr 1.2fr"><span>Counting method</span><span>Saṁyutta (SN)</span><span>Aṅguttara (AN)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2.2fr 1.2fr 1.2fr"><span>Modern translated editions (e.g. Bhikkhu Bodhi)</span><span style="color:var(--d-acc)!important"><strong>~2,889 ★</strong></span><span>~2,344</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:2.2fr 1.2fr 1.2fr"><span>Traditional Pāli commentary (repetition series expanded)</span><span>~7,762</span><span style="color:var(--d-acc)!important"><strong>~9,557 ★</strong></span></div>' +
          '</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">So the honest answer is: <em>Saṁyutta or Aṅguttara, depending on the counting convention</em> — there\'s no single agreed number. Khuddaka sits outside this contest; it\'s a shelf of separate books rather than one stream of numbered suttas.</div>',
        answer: ''
      },
      {
        question: 'What is the Abhidhamma? I\'ve heard it\'s very different from the suttas.',
        toolName: 'list_structure',
        toolArgs: '',
        statuses: ['querying…', 'Abhidhamma structure loaded'],
        toolDur: 1.5,
        dur: 32,
        type: 'chat',
        html:
          '<div class="mcd-cp">The <strong>Abhidhamma Piṭaka</strong> ("Higher Teaching") is the third basket — a systematic philosophical re-analysis of the entire Dhamma. Where the suttas give teachings in narrative and dialogue, the Abhidhamma strips out the story and maps every mental and material phenomenon through exhaustive lists and conditional relations. It contains <strong>7 books, 88,414 segments</strong>. No English translation is currently indexed (the bilara-data carries Pāli only).</div>' +
          '<div class="mcd-ctable">' +
            '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.8fr 1.8fr 1fr 2.2fr"><span>Pāli name</span><span>English name</span><span>Segments</span><span>What it does</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.8fr 1fr 2.2fr"><span class="mcd-tpali">Dhammasaṅgaṇī</span><span>Enumeration of Phenomena</span><span>7,777</span><span>Classifies all mental and material phenomena</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.8fr 1fr 2.2fr"><span class="mcd-tpali">Vibhaṅga</span><span>Book of Analysis</span><span>12,625</span><span>Analyzes major doctrinal categories (aggregates, elements, truths)</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.8fr 1fr 2.2fr"><span class="mcd-tpali">Dhātukathā</span><span>Discussion of Elements</span><span>3,001</span><span>Relates phenomena to aggregates, bases, and elements</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.8fr 1fr 2.2fr"><span class="mcd-tpali">Puggalapaññatti</span><span>Designation of Persons</span><span>1,841</span><span>Catalogs types of persons by their stage and character</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.8fr 1fr 2.2fr"><span class="mcd-tpali">Kathāvatthu</span><span>Points of Controversy</span><span>19,619</span><span>Refutes 252 non-Theravāda doctrinal positions</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.8fr 1fr 2.2fr"><span class="mcd-tpali">Yamaka</span><span>Book of Pairs</span><span>14,382</span><span>Twin questions applied to each term — forward and reverse</span></div>' +
            '<div class="mcd-trow" style="grid-template-columns:1.8fr 1.8fr 1fr 2.2fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Paṭṭhāna ★</span><span>Book of Conditional Relations</span><span>29,169</span><span>24 conditional relations applied exhaustively to all phenomena</span></div>' +
          '</div>' +
          '<div class="mcd-cp" style="margin-bottom:6px">The Paṭṭhāna is the largest and most technically demanding: 728 sections applying 24 types of conditionality to every phenomenon — traditionally said to be the text the Buddha taught in the fourth week after his awakening. It\'s often described as the most complex systematic text in world literature.</div>',
        answer: ''
      }]
    },
    {
      tab: 'search_by_keyword',
      scenarios: [
        {
          question: 'I keep seeing "anatta" in dharma books — where does it actually appear in the original Pali?',
          toolName: 'search_by_keyword',
          toolArgs: '"anatta"',
          statuses: ['searching Pāli index…', 'anatt* → 6 title matches'],
          toolDur: 2.5,
          dur: 22,
          type: 'chat',
          html:
            '<div class="mcd-cp">The keyword search matched 6 suttas whose <em>titles</em> contain "Anatta" — nearly all from SN 22, the Khandha-saṃyutta dedicated to the five aggregates.</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.9fr 3fr"><span>Sutta</span><span>Title (English)</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.9fr 3fr"><span class="mcd-tpali">SN 22.14</span><span>Not-Self</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.9fr 3fr"><span class="mcd-tpali">SN 22.68</span><span>Not-Self</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.9fr 3fr"><span class="mcd-tpali">SN 22.143</span><span>Not-Self</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.9fr 3fr"><span class="mcd-tpali">SN 23.17</span><span>Not-Self</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.9fr 3fr"><span class="mcd-tpali">SN 46.73</span><span>Not-Self in Suffering</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.9fr 3fr"><span class="mcd-tpali">AN 6.100</span><span>Not-Self</span></div>' +
            '</div>' +
            '<div class="mcd-cp">These are all title matches — the body text uses inflected Pāli forms like <em>anattā</em> (nominative) and <em>anattato</em> (ablative), not the bare stem. The most famous discourse on non-self is <strong>SN 22.59</strong>, the <em>Anattalakkhaṇasutta</em> ("Discourse on the Characteristic of Non-Self") — it has a longer title with <em>lakkhaṇa</em> added, which is why it didn\'t appear here.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn22.59" target="_blank" rel="noopener">SN 22.59</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn22.68" target="_blank" rel="noopener">SN 22.68</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn46.73" target="_blank" rel="noopener">SN 46.73</a></div>',
          answer: ''
        },
        {
          question: 'My teacher always mentions the Metta Sutta — is it actually in the Canon?',
          toolName: 'search_by_keyword',
          toolArgs: '"metta", language="pali"',
          statuses: ['searching Pāli index…', 'metta → 4 title matches'],
          toolDur: 2.3,
          dur: 20,
          type: 'chat',
          html:
            '<div class="mcd-cp">Yes — the Metta Sutta is in the Canon, and it appears in <strong>two places</strong> with the same text.</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.9fr 1.5fr 2fr"><span>Sutta</span><span>Collection</span><span>Title (English)</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.9fr 1.5fr 2fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Kp 9 ★</span><span>Khuddakapāṭha</span><span>The Discourse on Love</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.9fr 1.5fr 2fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Snp 1.8 ★</span><span>Sutta Nipāta</span><span>The Discourse on Love</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.9fr 1.5fr 2fr"><span class="mcd-tpali">AN 7.62</span><span>Aṅguttara Nikāya</span><span>Don\'t Fear Good Deeds</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.9fr 1.5fr 2fr"><span class="mcd-tpali">Iti 22</span><span>Itivuttaka</span><span>The Benefits of Love</span></div>' +
            '</div>' +
            '<div class="mcd-cp"><strong>Kp 9</strong> (Khuddakapāṭha) is the chanting version — the first sutta in the Minor Anthologies, recited in Theravāda ceremonies. <strong>Snp 1.8</strong> is the canonical location in the Sutta Nipāta. Both open identically:</div>' +
            '<div class="mcd-cverse"><em>Karaṇīyamatthakusalena</em><br>"What should be done by one skilled in good,<br>who wants to attain the state of peace..."</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">AN 7.62 and Iti 22 are separate, shorter discourses on the benefits of <em>mettā</em> practice.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/kp9" target="_blank" rel="noopener">Kp 9</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/snp1.8" target="_blank" rel="noopener">Snp 1.8</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/an7.62" target="_blank" rel="noopener">AN 7.62</a></div>',
          answer: ''
        },
        {
          question: 'I heard a monk tried to split the Buddhist community in the Buddha\'s time — what does the Canon say?',
          toolName: 'search_by_keyword',
          toolArgs: '"Devadatta"',
          statuses: ['searching Pāli index…', 'Devadatta → 6 Vinaya segments'],
          toolDur: 2.7,
          dur: 22,
          type: 'chat',
          html:
            '<div class="mcd-cp">All 6 results come from the <strong>Vinaya Piṭaka</strong>, not the Suttas — the Devadatta affair is a monastic-discipline story, so the Canon preserves it in the rules section rather than in discourses.</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.6fr 3fr"><span>Source</span><span>Section</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.6fr 3fr"><span class="mcd-tpali">pli-tv-kd17</span><span>Khandhaka 17 — the chapter dealing with the Devadatta affair</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.6fr 3fr"><span class="mcd-tpali">pli-tv-bu-vb-ss10</span><span>Saṅghādisesa 10 — the rule against causing a schism</span></div>' +
            '</div>' +
            '<div class="mcd-ch3">The story in brief</div>' +
            '<div class="mcd-cp">Devadatta proposed five strict rules to the Buddha (living only in forests, eating only alms food, wearing only patchwork robes, sleeping under trees, abstaining from fish and meat). The Buddha refused to make them mandatory. Devadatta led a breakaway group, and the Buddha\'s verdict is recorded in the chapter:</div>' +
            '<div class="mcd-cverse"><em>Garuko kho, devadatta, saṅghabhedo</em><br>"Schism in the Sangha is a serious matter, Devadatta."</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">Saṅghādisesa 10 (pli-tv-bu-vb-ss10) was formulated directly from this episode — it prohibits a monk from working to split a unified community and is one of the most serious offence categories in the Vinaya.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/pli-tv-kd17" target="_blank" rel="noopener">pli-tv-kd17</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/pli-tv-bu-vb-ss10" target="_blank" rel="noopener">Ss 10</a></div>',
          answer: ''
        }
      ]
    },
    {
      tab: 'search_semantic',
      scenarios: [
        {
          question: 'I want to find passages where the Buddha actually describes what liberation or peace feels like',
          toolName: 'search_semantic',
          toolArgs: '"the feeling of peace and release after letting go of everything you were clinging to"',
          statuses: ['embedding query…', 'vector search complete'],
          toolDur: 1.5,
          dur: 28,
          type: 'chat',
          html:
            '<div class="mcd-cp">All 5 results feature the <em>same canonical Pāli formula</em> for nibbāna — appearing verbatim in 4 different suttas across the Aṅguttara Nikāya.</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.8fr 4fr 0.8fr"><span>Sutta</span><span>English (Sujato)</span><span>Dist.</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 4fr 0.8fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">AN 10.60 ★</span><span>"This is peaceful; this is sublime — the stilling of all activities, the letting go of all attachments, the ending of craving, fading away, extinguishment."</span><span>0.361</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 4fr 0.8fr"><span class="mcd-tpali">AN 3.32</span><span>same formula (+ "cessation")</span><span>0.363</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 4fr 0.8fr"><span class="mcd-tpali">AN 10.6</span><span>same formula</span><span>0.363</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 4fr 0.8fr"><span class="mcd-tpali">AN 9.36</span><span>same formula ×2 (appears in §8 and §9)</span><span>0.363</span></div>' +
            '</div>' +
            '<div class="mcd-cverse"><em>etaṁ santaṁ etaṁ paṇītaṁ yadidaṁ sabbasaṅkhārasamatho<br>sabbūpadhipaṭinissaggo taṇhākkhayo virāgo nirodho nibbānan</em><br>"This is peaceful; this is sublime — the stilling of all activities,<br>the letting go of all attachments, the ending of craving,<br>fading away, cessation, extinguishment."</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">This is the standard formula a disciple meditates on as a contemplation of nibbāna. A keyword search for "peace" or "liberation" would miss most instances; semantic search found all four suttas from a plain-language description of the <em>feeling</em>.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/an10.60" target="_blank" rel="noopener">AN 10.60</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/an3.32" target="_blank" rel="noopener">AN 3.32</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/an9.36" target="_blank" rel="noopener">AN 9.36</a></div>',
          answer: ''
        },
        {
          question: 'I keep hearing Buddhism is all about suffering — but does the Canon ever talk about happiness or joy?',
          toolName: 'search_semantic',
          toolArgs: '"the joy and lightness that arises when the mind becomes clear and undisturbed"',
          statuses: ['embedding query…', 'vector search complete'],
          toolDur: 1.5,
          dur: 28,
          type: 'chat',
          html:
            '<div class="mcd-cp">The two closest results are back-to-back verses from Dhammapada chapter 3 — the <em>Cittavagga</em>, the "Mind" chapter. The third is a prose passage from SN 35.97.</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.8fr 3.8fr 0.8fr"><span>Sutta</span><span>English (Sujato)</span><span>Dist.</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 3.8fr 0.8fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Dhp 35 ★</span><span><strong>"a tamed mind leads to bliss."</strong></span><span>0.276</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 3.8fr 0.8fr"><span class="mcd-tpali">Dhp 36</span><span>"a guarded mind leads to bliss."</span><span>0.327</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 3.8fr 0.8fr"><span class="mcd-tpali">SN 35.97</span><span>"When the mind isn\'t polluted, joy springs up."</span><span>0.327</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 3.8fr 0.8fr"><span class="mcd-tpali">SN 5.2</span><span>"when the mind is serene"</span><span>0.338</span></div>' +
            '</div>' +
            '<div class="mcd-cverse"><em>Cittaṁ dantaṁ sukhāvahaṁ</em> — Dhp 35<br>"A tamed mind leads to bliss."<br><em>Cittaṁ guttaṁ sukhāvahaṁ</em> — Dhp 36<br>"A guarded mind leads to bliss."</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">The Canon distinguishes <em>dukkha</em> (the unsatisfactoriness of conditioned existence) from <em>sukha</em> (genuine happiness). These results all say the same thing: joy isn\'t found by seeking pleasure but by working with the mind. Neither "happiness" nor "joy" appears in the matched Pāli — the semantic match worked across the translation gap.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dhp33-43" target="_blank" rel="noopener">Dhp 33–43</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn35.97" target="_blank" rel="noopener">SN 35.97</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn5.2" target="_blank" rel="noopener">SN 5.2</a></div>',
          answer: ''
        },
        {
          question: 'Are there any poems or verses in the Canon about monks meditating alone in the forest?',
          toolName: 'search_semantic',
          toolArgs: '"a monk who lives alone in the forest content with little"',
          statuses: ['embedding query…', 'vector search complete'],
          toolDur: 1.5,
          dur: 28,
          type: 'chat',
          html:
            '<div class="mcd-cp">Semantic search surfaced results from three different layers of the Canon — Vinaya (procedural narrative), Sutta Nipāta (verse), and the Theragāthā (personal poems of awakened elders).</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:0.8fr 3.8fr 0.8fr"><span>Sutta</span><span>English (Sujato)</span><span>Dist.</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 3.8fr 0.8fr"><span class="mcd-tpali">Vinaya Pj 4</span><span>"At one time a monk lived in the wilderness."</span><span>0.285</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 3.8fr 0.8fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Snp 1.9 ★</span><span>"the sage meditating alone in the forest"</span><span>0.307</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 3.8fr 0.8fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Thag 10.2 ★</span><span>"to be dwelling alone in a forest grove."</span><span>0.316</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:0.8fr 3.8fr 0.8fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">Thag 6.11 ★</span><span>"while dwelling in a forest grove"</span><span>0.323</span></div>' +
            '</div>' +
            '<div class="mcd-cverse"><em>Muniṁ vanasmiṁ jhāyantaṁ</em><br>"the sage meditating alone in the forest"<br><span style="color:var(--d-dim);font-size:11px">— Snp 1.9 (Hemavatasutta)</span></div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">The <strong>Theragāthā</strong> (Verses of the Elder Monks) collects personal spiritual poetry by the direct disciples of the Buddha. Thag 10.2 and Thag 6.11 are genuine verses by named elders describing their own forest practice — the kind of result a keyword search for "forest" or "monk" would likely miss.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/snp1.9" target="_blank" rel="noopener">Snp 1.9</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/thag10.2" target="_blank" rel="noopener">Thag 10.2</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/thag6.11" target="_blank" rel="noopener">Thag 6.11</a></div>',
          answer: ''
        }
      ]
    },
    {
      tab: 'get_reference',
      scenarios: [
        {
          question: 'What\'s the correct citation for the Buddha\'s first ever discourse — the one about the Four Noble Truths?',
          toolName: 'get_reference',
          toolArgs: '"sn56.11"',
          statuses: ['looking up sn56.11…', 'citation ready'],
          toolDur: 0.6,
          dur: 18,
          type: 'chat',
          html:
            '<div class="mcd-cverse">"2. Rolling Forth the Wheel of Dhamma<br>(2. Dhammacakkappavattanavagga, SN56.11), Connected Discourses"<br><span style="color:var(--d-dim);font-size:11px">— citation string returned by the API</span></div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.5fr 3fr"><span>Field</span><span>Value</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Pāli title</span><span class="mcd-tpali">Dhammacakkappavattanavagga</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>English title</span><span>Rolling Forth the Wheel of Dhamma</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Nikāya</span><span>Saṁyuttanikāya — Connected Discourses (SN)</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Piṭaka</span><span>Suttantapiṭaka — Basket of Discourses</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Segments</span><span>60</span></div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">The "2." prefix in the title is the vagga (chapter) number — strip it for academic use. Full citation: "Bhikkhu Sujato, trans., <em>Rolling Forth the Wheel of Dhamma</em> (Dhammacakkappavattanasutta, SN 56.11), Connected Discourses, SuttaCentral, CC0."</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn56.11" target="_blank" rel="noopener">SN 56.11</a></div>',
          answer: ''
        },
        {
          question: 'I want to cite the Parable of the Raft — what\'s the full reference for that sutta?',
          toolName: 'get_reference',
          toolArgs: '"mn22"',
          statuses: ['looking up mn22…', 'citation ready'],
          toolDur: 0.6,
          dur: 20,
          type: 'chat',
          html:
            '<div class="mcd-cverse">"The Simile of the Cobra (Alagaddūpamasutta, MN22), Middle Discourses"<br><span style="color:var(--d-dim);font-size:11px">— citation string returned by the API</span></div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.5fr 3fr"><span>Field</span><span>Value</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Pāli title</span><span class="mcd-tpali">Alagaddūpamasutta</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>English title</span><span>The Simile of the Cobra</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Nikāya</span><span>Majjhimanikāya — Middle Discourses (MN)</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Piṭaka</span><span>Suttantapiṭaka — Basket of Discourses</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Segments</span><span>359</span></div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">The sutta\'s official title is <strong>The Simile of the Cobra</strong> (<em>Alagaddūpama</em> = cobra/snake), named after the opening simile about mishandling a snake. The Parable of the Raft — the teaching that the Dhamma is "like a raft, for crossing, not for carrying" — is in §§13–14 of the same 359-segment sutta. Full citation: "Bhikkhu Sujato, trans., <em>The Simile of the Cobra</em> (Alagaddūpamasutta, MN22), Middle Discourses, SuttaCentral, CC0."</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn22" target="_blank" rel="noopener">MN 22</a></div>',
          answer: ''
        },
        {
          question: 'I want to reference the sutta about the Buddha\'s final days and death — how do I cite it?',
          toolName: 'get_reference',
          toolArgs: '"dn16"',
          statuses: ['looking up dn16…', 'citation ready'],
          toolDur: 0.6,
          dur: 20,
          type: 'chat',
          html:
            '<div class="mcd-cverse">"The Great Discourse on the Buddha\'s Extinguishment<br>(Mahāparinibbānasutta, DN16), Long Discourses"<br><span style="color:var(--d-dim);font-size:11px">— citation string returned by the API</span></div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.5fr 3fr"><span>Field</span><span>Value</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Pāli title</span><span class="mcd-tpali">Mahāparinibbānasutta</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>English title</span><span>The Great Discourse on the Buddha\'s Extinguishment</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Nikāya</span><span>Dīghanikāya — Long Discourses (DN)</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Piṭaka</span><span>Suttantapiṭaka — Basket of Discourses</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 3fr"><span>Segments</span><span style="color:var(--d-acc)!important"><strong>1,664</strong> — longest sutta in the Canon</span></div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">At 1,664 segments, DN 16 is the longest sutta in the Pāli Canon — it spans the Buddha\'s final three months, from his last journey through Vesālī to his passing at Kusinārā. Full citation: "Bhikkhu Sujato, trans., <em>The Great Discourse on the Buddha\'s Extinguishment</em> (Mahāparinibbānasutta, DN16), Long Discourses, SuttaCentral, CC0."</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/dn16" target="_blank" rel="noopener">DN 16</a></div>',
          answer: ''
        }
      ]
    },
    {
      tab: 'parse_pali_word',
      scenarios: [
        {
          question: 'I\'m reading about the Second Noble Truth and keep seeing the word "tanhāya" — what grammatical form is that?',
          toolName: 'parse_pali_word',
          toolArgs: '"tanhāya"',
          statuses: ['stripping suffixes…', 'stems found'],
          toolDur: 0.4,
          dur: 20,
          type: 'chat',
          html:
            '<div class="mcd-cp">Pāli nouns inflect across 7 cases × 2 numbers. <em>parse_pali_word</em> strips the ending to recover the dictionary stem.</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1fr 1.5fr 2.5fr"><span>Input</span><span>Suffix removed</span><span>Meaning of the ending</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1fr 1.5fr 2.5fr"><span class="mcd-tpali">tanhāya</span><span class="mcd-tpali">-āya</span><span>Dative <em>or</em> Ablative singular — ā-stem nouns use the same form for both</span></div>' +
            '</div>' +
            '<div class="mcd-ch3">Possible stems — pick the real one</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.5fr 0.5fr 3fr"><span>Stem</span><span>Valid?</span><span>Note</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.5fr 3fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">tanhā ★</span><span>✓</span><span>Real dictionary word — craving, thirst</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.5fr 3fr"><span class="mcd-tpali">tanha</span><span>—</span><span>Simplified spelling, not standard Pāli</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.5fr 3fr"><span class="mcd-tpali">tanhāya</span><span>—</span><span>Artifact (the original input returned as-is)</span></div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px"><em>Taṇhā</em> (craving/thirst) is the central concept of the Second Noble Truth: craving is what causes suffering. The <strong>-āya</strong> ending on an ā-stem serves double duty — dative ("toward craving") and ablative ("from craving"). Context determines which: in the Second Noble Truth formula, it is ablative — suffering <em>arises from</em> taṇhā.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn56.11" target="_blank" rel="noopener">SN 56.11</a></div>',
          answer: ''
        },
        {
          question: 'I found "kusalāni" in a text about cultivating good qualities — what exactly does this form mean?',
          toolName: 'parse_pali_word',
          toolArgs: '"kusalāni"',
          statuses: ['stripping suffixes…', 'stems found'],
          toolDur: 0.4,
          dur: 20,
          type: 'chat',
          html:
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1fr 1.5fr 2.5fr"><span>Input</span><span>Suffix removed</span><span>Meaning of the ending</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1fr 1.5fr 2.5fr"><span class="mcd-tpali">kusalāni</span><span class="mcd-tpali">-āni</span><span>Nominative / Accusative plural neuter — "wholesome things"</span></div>' +
            '</div>' +
            '<div class="mcd-ch3">Possible stems — pick the real one</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.5fr 0.5fr 3fr"><span>Stem</span><span>Valid?</span><span>Note</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.5fr 3fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">kusala ★</span><span>✓</span><span>Wholesome, skillful — key ethical term</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.5fr 3fr"><span class="mcd-tpali">kusalāi</span><span>—</span><span>Artifact</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.5fr 3fr"><span class="mcd-tpali">kusalāu</span><span>—</span><span>Artifact</span></div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px"><em>Kusala</em> (wholesome/skillful) is one of the most frequent ethical terms in the Canon. The <strong>-āni</strong> ending marks neuter nouns in the nominative or accusative plural — <em>kusalāni</em> = "wholesome things/actions." It appears in stock phrases like <em>sabbāni kusalāni dhammāni</em> ("all wholesome qualities") and as the object of <em>samādapeti</em> ("encourages [in wholesome actions]") throughout the Suttas.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn8" target="_blank" rel="noopener">MN 8</a><a class="mcd-chip" href="https://tripitaka-mcp.com/read/an10.176" target="_blank" rel="noopener">AN 10.176</a></div>',
          answer: ''
        },
        {
          question: 'The Buddha seems to say "bhikkhave" constantly — what word is that exactly?',
          toolName: 'parse_pali_word',
          toolArgs: '"bhikkhave"',
          statuses: ['stripping suffixes…', 'stems found'],
          toolDur: 0.4,
          dur: 22,
          type: 'chat',
          html:
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1fr 1.5fr 2.5fr"><span>Input</span><span>Suffix removed</span><span>Meaning of the ending</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1fr 1.5fr 2.5fr"><span class="mcd-tpali">bhikkhave</span><span class="mcd-tpali">-e</span><span>Vocative plural — direct address: "O monks!"</span></div>' +
            '</div>' +
            '<div class="mcd-ch3">Possible stems — <em>none match the real entry</em></div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.5fr 0.5fr 3fr"><span>Stem returned</span><span>Valid?</span><span>Note</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.5fr 3fr"><span class="mcd-tpali">bhikkhava</span><span>—</span><span>Rule-based artifact — not a real Pāli word</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.5fr 3fr"><span class="mcd-tpali">bhikkhave</span><span>—</span><span>The original input returned as-is</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.5fr 0.5fr 3fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">bhikkhu ★</span><span>✓</span><span>The real stem — look up in <em>get_word_definition</em></span></div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px"><strong>Bhikkhave</strong> is the vocative plural of <em>bhikkhu</em> (monk/mendicant) — it means "O monks!" and is the most common opening address in the entire Canon. The parser correctly identifies the <strong>-e</strong> ending but returns <em>bhikkhava</em> as the stem; that\'s an artifact. <em>Bhikkhu</em> is a u-stem noun, and the vocative plural of u-stem nouns involves a vowel change (u → ave) that the rule-based parser doesn\'t model. This is a known limitation — the stem to look up is <em>bhikkhu</em>, not the parser\'s output.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/sn56.11" target="_blank" rel="noopener">SN 56.11</a></div>',
          answer: ''
        }
      ]
    },
    {
      tab: 'list_editions',
      scenarios: [
        {
          question: 'What translation editions are available on this server? Which translators are included?',
          toolName: 'list_editions',
          toolArgs: '',
          statuses: ['querying editions…', 'editions loaded'],
          toolDur: 0.5,
          dur: 22,
          type: 'chat',
          html:
            '<div class="mcd-cp"><em>list_editions</em> returns every translation indexed on the running server — edition code, translator, language, and load status. Call this before <em>compare_translations</em> to confirm which codes are valid for this instance.</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.2fr 1.8fr 0.7fr 1.4fr"><span>Code</span><span>Translator</span><span>Lang</span><span>Status</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 0.7fr 1.4fr"><span class="mcd-tpali">pali</span><span>—</span><span>Pāli</span><span>✓ always present</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 0.7fr 1.4fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">sujato ★</span><span>Bhikkhu Sujato</span><span>EN</span><span>✓ loaded — Sutta Piṭaka</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 0.7fr 1.4fr"><span class="mcd-tpali">brahmali</span><span>Bhikkhu Brahmali</span><span>EN</span><span>✓ loaded — Vinaya</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 0.7fr 1.4fr"><span class="mcd-tpali" style="color:var(--d-fg2)">dhiranandi</span><span style="color:var(--d-fg2)">Phra Dhiranandi</span><span style="color:var(--d-fg2)">TH</span><span style="color:var(--d-fg2)">pending</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 0.7fr 1.4fr"><span class="mcd-tpali" style="color:var(--d-fg2)">jayasaro</span><span style="color:var(--d-fg2)">Ajahn Jayasaro</span><span style="color:var(--d-fg2)">TH</span><span style="color:var(--d-fg2)">pending</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 0.7fr 1.4fr"><span class="mcd-tpali" style="color:var(--d-fg2)">mbu</span><span style="color:var(--d-fg2)">Mahamakut</span><span style="color:var(--d-fg2)">TH</span><span style="color:var(--d-fg2)">pending</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 0.7fr 1.4fr"><span class="mcd-tpali" style="color:var(--d-fg2)">royal</span><span style="color:var(--d-fg2)">Royal Institute</span><span style="color:var(--d-fg2)">TH</span><span style="color:var(--d-fg2)">pending</span></div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">Three editions are live now: Pāli original, Sujato English (Sutta Piṭaka), and Brahmali English (Vinaya). Four Thai editions — Dhiranandi, Jayasaro, Mahamakut, and Royal — are indexed and pending final verification before release.</div>',
          answer: ''
        },
        {
          question: 'Which edition codes do I need to pass to compare_translations? I want to see Pāli and English side by side.',
          toolName: 'list_editions',
          toolArgs: '',
          statuses: ['querying editions…', 'editions loaded'],
          toolDur: 0.5,
          dur: 20,
          type: 'chat',
          html:
            '<div class="mcd-cp">The edition codes from <em>list_editions</em> are exactly what you pass to <em>compare_translations</em>. Only editions marked <em>loaded</em> work right now — the three usable codes are:</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1fr 2fr 2.5fr"><span>Code</span><span>What it gives you</span><span>Example</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1fr 2fr 2.5fr"><span class="mcd-tpali">pali</span><span>Original Pāli text</span><span><code>editions=["pali","sujato"]</code></span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1fr 2fr 2.5fr"><span class="mcd-tpali" style="color:var(--d-acc)!important">sujato ★</span><span>Sujato English</span><span><code>editions=["sujato"]</code> (default)</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1fr 2fr 2.5fr"><span class="mcd-tpali">brahmali</span><span>Brahmali English — Vinaya only</span><span><code>editions=["pali","brahmali"]</code></span></div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">If you pass an edition code that is not loaded, <em>compare_translations</em> returns an error listing the valid codes for this server. Four Thai editions are planned — once released, <code>editions=["pali","sujato","jayasaro"]</code> will enable trilingual comparison.</div>',
          answer: ''
        },
        {
          question: 'My study group reads Thai — does this database include a Thai translation?',
          toolName: 'list_editions',
          toolArgs: '',
          statuses: ['querying editions…', 'editions loaded'],
          toolDur: 0.5,
          dur: 22,
          type: 'chat',
          html:
            '<div class="mcd-cp"><em>list_editions</em> shows four Thai translation projects in the database, all currently marked <em>pending</em> — indexed but not yet released. Here is what each one covers:</div>' +
            '<div class="mcd-ctable">' +
              '<div class="mcd-trow mcd-thr" style="grid-template-columns:1.2fr 1.8fr 2.5fr"><span>Code</span><span>Translator</span><span>Notes</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 2.5fr"><span class="mcd-tpali" style="color:var(--d-fg2)">dhiranandi</span><span style="color:var(--d-fg2)">Phra Dhiranandi</span><span style="color:var(--d-fg2)">Modern Thai prose, Sutta Piṭaka focus</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 2.5fr"><span class="mcd-tpali" style="color:var(--d-fg2)">jayasaro</span><span style="color:var(--d-fg2)">Ajahn Jayasaro</span><span style="color:var(--d-fg2)">Contemporary Thai — Forest tradition voice</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 2.5fr"><span class="mcd-tpali" style="color:var(--d-fg2)">mbu</span><span style="color:var(--d-fg2)">Mahamakut</span><span style="color:var(--d-fg2)">Mahamakut Buddhist University edition</span></div>' +
              '<div class="mcd-trow" style="grid-template-columns:1.2fr 1.8fr 2.5fr"><span class="mcd-tpali" style="color:var(--d-fg2)">royal</span><span style="color:var(--d-fg2)">Royal Institute</span><span style="color:var(--d-fg2)">Thai Tipiṭaka Foundation official edition</span></div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">Until a Thai edition is released, <code>editions=["pali","sujato"]</code> is the best available combination. Once <em>jayasaro</em> or <em>dhiranandi</em> goes live, trilingual study — Pāli · English · Thai — will be a single <em>compare_translations</em> call.</div>',
          answer: ''
        }
      ]
    },
    {
      tab: 'open_sutta_viewer',
      scenarios: [
        {
          question: 'Can you open the Mindfulness of Breathing sutta right at the part where the Buddha describes sitting down and starting the practice?',
          toolName: 'open_sutta_viewer',
          toolArgs: '"mn118", around="mn118:17.1"',
          statuses: ['loading MN 118…', 'viewer centred at §17.1'],
          toolDur: 1.1,
          dur: 28,
          type: 'chat',
          html:
            '<div class="mcd-cp"><em>open_sutta_viewer</em> renders a Pāli / English reader panel centred on a specific segment (▶). The highlighted row is the jump target; the viewer shows ±12 segments of context on each side. MN 118 · Ānāpānassatisutta has 154 segments total — this opens at step one of the 16-step breath practice.</div>' +
            '<div class="mcd-vwr">' +
              '<div class="mcd-vhdr"><span>MN 118 · Ānāpānassatisutta · Mindfulness of Breathing</span><span style="color:var(--d-dim)">154 seg</span></div>' +
              '<div class="mcd-vsegs">' +
                '<div class="mcd-vseg"><div class="mcd-sid">mn118:15.1</div><div class="mcd-vp">Ānāpānassati, bhikkhave, bhāvitā bahulīkatā mahapphalā hoti mahānisaṁsā.</div><div class="mcd-ve">Mendicants, when mindfulness of breathing is developed and cultivated it is very fruitful and beneficial.</div></div>' +
                '<div class="mcd-vseg"><div class="mcd-sid">mn118:16.1</div><div class="mcd-vp">Kathaṁ bhāvitā ca, bhikkhave, ānāpānassati kathaṁ bahulīkatā mahapphalā hoti mahānisaṁsā?</div><div class="mcd-ve">And how is mindfulness of breathing developed and cultivated to be very fruitful and beneficial?</div></div>' +
                '<div class="mcd-vseg hi"><div class="mcd-sid">mn118:17.1 ▶</div><div class="mcd-vp">Idha, bhikkhave, bhikkhu araññagato vā rukkhamūlagato vā suññāgāragato vā nisīdati pallaṅkaṁ ābhujitvā ujuṁ kāyaṁ paṇidhāya parimukhaṁ satiṁ upaṭṭhapetvā.</div><div class="mcd-ve">It\'s when a mendicant—gone to a wilderness, or to the root of a tree, or to an empty hut—sits down cross-legged, sets their body straight, and brings mindfulness to the present.</div></div>' +
                '<div class="mcd-vseg"><div class="mcd-sid">mn118:17.2</div><div class="mcd-vp">So satova assasati satova passasati.</div><div class="mcd-ve">Just mindful, they breathe in. Mindful, they breathe out.</div></div>' +
              '</div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">The 16 steps of ānāpānassati begin at §18 and cover all four satipaṭṭhānas — body, feeling tone, mind, and phenomena. Use <em>open_sutta_viewer</em> after a search hit: pass the returned <em>segment_id</em> as <em>around</em> to jump to exactly the cited line.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/mn118#mn118:17.1" target="_blank" rel="noopener">MN 118 §17.1</a></div>',
          answer: ''
        },
        {
          question: 'I heard the Attadaṇḍa Sutta is one of the most personal poems the Buddha ever spoke — can you open it?',
          toolName: 'open_sutta_viewer',
          toolArgs: '"snp4.15", around="snp4.15:1.1"',
          statuses: ['loading snp4.15…', 'viewer centred at §1.1'],
          toolDur: 1.1,
          dur: 28,
          type: 'chat',
          html:
            '<div class="mcd-cp"><em>Attadaṇḍasutta</em> (Snp 4.15, "Taking Up Arms") is considered one of the most autobiographical suttas in the Canon — the Buddha describes his own response to witnessing human violence and how urgency drove him toward renunciation. Snp 4 (the Aṭṭhakavagga) is among the oldest strata. 84 segments, all verse.</div>' +
            '<div class="mcd-vwr">' +
              '<div class="mcd-vhdr"><span>Snp 4.15 · Attadaṇḍasutta · Taking Up Arms</span><span style="color:var(--d-dim)">84 seg</span></div>' +
              '<div class="mcd-vsegs">' +
                '<div class="mcd-vseg"><div class="mcd-sid">snp4.15:0.2</div><div class="mcd-vp">Attadaṇḍasutta</div><div class="mcd-ve">Taking Up Arms</div></div>' +
                '<div class="mcd-vseg hi"><div class="mcd-sid">snp4.15:1.1 ▶</div><div class="mcd-vp">Attadaṇḍā bhayaṁ jātaṁ,</div><div class="mcd-ve">Peril stems from those who take up arms—</div></div>' +
                '<div class="mcd-vseg"><div class="mcd-sid">snp4.15:1.2</div><div class="mcd-vp">janaṁ passatha medhagaṁ;</div><div class="mcd-ve">just look how people conflict!</div></div>' +
                '<div class="mcd-vseg"><div class="mcd-sid">snp4.15:1.3</div><div class="mcd-vp">Saṁvegaṁ kittayissāmi,</div><div class="mcd-ve">I shall extol how I came to be</div></div>' +
                '<div class="mcd-vseg"><div class="mcd-sid">snp4.15:1.4</div><div class="mcd-vp">yathā saṁvijitaṁ mayā.</div><div class="mcd-ve">stirred with a sense of urgency.</div></div>' +
                '<div class="mcd-vseg"><div class="mcd-sid">snp4.15:2.1</div><div class="mcd-vp">Phandamānaṁ pajaṁ disvā,</div><div class="mcd-ve">I saw this population flounder,</div></div>' +
              '</div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">Each segment is one pāda (quarter-verse). The poem traces a journey from witnessing conflict, through fear and restlessness, to the discovery of inner stillness — ending with the Buddha describing his own attainment of peace. One of the few first-person accounts of awakening in the Canon.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/snp4.15#snp4.15:1.1" target="_blank" rel="noopener">Snp 4.15 §1.1</a></div>',
          answer: ''
        },
        {
          question: 'Can you open the Metta Sutta so I can read the Pāli and English side by side?',
          toolName: 'open_sutta_viewer',
          toolArgs: '"kp9", around="kp9:1.1"',
          statuses: ['loading kp9…', 'viewer centred at §1.1'],
          toolDur: 1.1,
          dur: 28,
          type: 'chat',
          html:
            '<div class="mcd-cp">kp9 (Khuddakapāṭha 9) is the shortest standalone sutta in the Canon — 44 segments, all verse. <em>open_sutta_viewer</em> renders the Pāli and Sujato English columns side by side for line-by-line study. Segment kp9:3.3 contains the metta dedication chanted in monasteries worldwide.</div>' +
            '<div class="mcd-vwr">' +
              '<div class="mcd-vhdr"><span>kp9 · Mettasutta · The Discourse on Love</span><span style="color:var(--d-dim)">44 seg</span></div>' +
              '<div class="mcd-vsegs">' +
                '<div class="mcd-vseg"><div class="mcd-sid">kp9:0.2</div><div class="mcd-vp">Mettasutta</div><div class="mcd-ve">The Discourse on Love</div></div>' +
                '<div class="mcd-vseg hi"><div class="mcd-sid">kp9:1.1 ▶</div><div class="mcd-vp">Karaṇīyamatthakusalena,</div><div class="mcd-ve">Those who are skilled in the meaning of scripture</div></div>' +
                '<div class="mcd-vseg"><div class="mcd-sid">kp9:1.2</div><div class="mcd-vp">Yanta santaṁ padaṁ abhisamecca;</div><div class="mcd-ve">should practice like this so as to realize the state of peace.</div></div>' +
                '<div class="mcd-vseg"><div class="mcd-sid">kp9:1.3</div><div class="mcd-vp">Sakko ujū ca suhujū ca,</div><div class="mcd-ve">Let them be capable and upright, very upright,</div></div>' +
                '<div class="mcd-vseg"><div class="mcd-sid">kp9:1.4</div><div class="mcd-vp">Sūvaco cassa mudu anatimānī.</div><div class="mcd-ve">easy to speak to, gentle and humble;</div></div>' +
                '<div class="mcd-vseg"><div class="mcd-sid">kp9:3.3</div><div class="mcd-vp">Sukhino va khemino hontu,</div><div class="mcd-ve" style="color:var(--d-acc)">May they be happy and safe!</div></div>' +
              '</div>' +
            '</div>' +
            '<div class="mcd-cp" style="margin-bottom:6px">The sutta opens with qualities the practitioner cultivates (kp9:1–2), then radiates metta outward in widening circles — from all nearby beings, to all directions, to all beings everywhere. It closes with the image of a mother protecting her only child as the model for unbounded loving-kindness.</div>' +
            '<div class="mcd-csrcs"><a class="mcd-chip" href="https://tripitaka-mcp.com/read/kp9#kp9:1.1" target="_blank" rel="noopener">kp9 §1.1</a></div>',
          answer: ''
        }
      ]
    }
  ];

  // ── CSS (injected once) ─────────────────────────────────────────────────────
  function injectCSS() {
    if (document.getElementById('mcd-css')) return;
    var el = document.createElement('style');
    el.id = 'mcd-css';
    el.textContent =
      '@import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap");' +
      '@keyframes mcd-blink{0%,49%{opacity:1}50%,100%{opacity:0}}' +
      '@keyframes mcd-spin{to{transform:rotate(360deg)}}' +
      '.mcd-outer{position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;border-radius:12px;' +
        'background:var(--d-outbg);box-shadow:0 1px 0 rgba(0,0,0,.07),0 18px 40px -18px rgba(0,0,0,.28);' +
        'margin:1.5rem 0 2rem}' +
      '.mcd-inner{position:absolute;top:0;left:0;width:1280px;height:720px;transform-origin:top left}' +
      '.mcd-bg{position:absolute;inset:0;background:var(--d-bg);display:flex;flex-direction:row;' +
        'box-sizing:border-box;font-family:system-ui,sans-serif}' +
      '.mcd-sidebar{width:175px;flex:none;display:flex;flex-direction:column;' +
        'padding:20px 8px 20px 16px;border-right:1px solid var(--d-brd);box-sizing:border-box}' +
      '.mcd-sidebtns{display:flex;gap:5px;flex:none;margin-top:10px}' +
      '.mcd-main{flex:1;min-width:0;display:flex;flex-direction:column;' +
        'padding:20px 28px 24px 12px;box-sizing:border-box}' +
      '.mcd-logo{font-family:"JetBrains Mono",monospace;font-size:13px;font-weight:600;color:var(--d-fg);' +
        'display:flex;align-items:center;gap:8px;flex:none;white-space:nowrap}' +
      '.mcd-ldot{width:7px;height:7px;border-radius:50%;background:var(--d-grn);' +
        'box-shadow:0 0 0 3px rgba(123,189,142,.16)}' +
      '.mcd-tabs{display:flex;flex-direction:column;gap:3px;flex:1;margin-top:12px;' +
        'overflow-y:auto;scrollbar-width:none}' +
      '.mcd-tabs::-webkit-scrollbar{display:none}' +
      '.mcd-tab{font-family:"JetBrains Mono",monospace;font-size:11px;font-weight:500;' +
        'padding:5px 8px;border-radius:5px;border:1px solid var(--d-brd2);background:transparent;' +
        'color:var(--d-fg2);cursor:pointer;white-space:nowrap;text-align:left;width:100%;' +
        'box-sizing:border-box;transition:all .15s}' +
      '.mcd-tab.on{background:var(--d-abg);border-color:var(--d-acc);color:var(--d-acc)}' +
      '.mcd-tab:hover:not(.on){border-color:var(--d-acc);color:var(--d-fg)}' +
      '.mcd-subtabs{display:none;flex-direction:column;gap:1px;padding:2px 0 4px 8px;' +
        'border-left:1px solid var(--d-brd);margin:0 0 4px 8px}' +
      '.mcd-subtabs.on{display:flex}' +
      '.mcd-stab{font-size:10.5px;line-height:1.35;padding:3px 6px;border-radius:4px;' +
        'border:none;color:var(--d-dim);cursor:pointer;text-align:left;width:100%;' +
        'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;box-sizing:border-box;' +
        'background:transparent;transition:color .15s,background .15s;font-family:inherit}' +
      '.mcd-stab.on{color:var(--d-acc);background:var(--d-abg)}' +
      '.mcd-stab:hover:not(.on){color:var(--d-fg2);background:var(--d-hbg)}' +
      '.mcd-tbtn{width:28px;height:28px;border-radius:6px;border:1px solid var(--d-brd2);' +
        'background:transparent;color:var(--d-fg2);cursor:pointer;flex:none;' +
        'display:flex;align-items:center;justify-content:center;font-size:13px;transition:all .15s}' +
      '.mcd-tbtn:hover{border-color:var(--d-acc);color:var(--d-acc)}' +
      '.mcd-frame{flex:1;background:var(--d-bg2);border:1px solid var(--d-brd);border-radius:11px;' +
        'padding:20px 24px;display:flex;flex-direction:column;min-height:0;overflow:hidden;' +
        'box-sizing:border-box}' +
      '.mcd-qrow{display:flex;justify-content:flex-end;flex:none;margin-bottom:14px}' +
      '.mcd-qbub{background:var(--d-qbg);color:var(--d-qfg);font-size:17px;line-height:1.5;' +
        'padding:11px 17px;border-radius:15px 15px 4px 15px;max-width:620px;letter-spacing:-.01em}' +
      '.mcd-cur{display:inline-block;width:2px;height:16px;background:var(--d-qfg);margin-left:2px;' +
        'vertical-align:-3px;animation:mcd-blink 1s steps(1) infinite}' +
      '.mcd-tool{border:1px solid var(--d-brd);border-radius:9px;background:var(--d-bg3);' +
        'overflow:hidden;margin-bottom:11px;flex:none}' +
      '.mcd-thd{display:flex;align-items:center;gap:8px;padding:8px 12px;border-bottom:1px solid var(--d-brd)}' +
      '.mcd-spin{width:12px;height:12px;border-radius:50%;border:2px solid var(--d-abg);' +
        'border-top-color:var(--d-acc);animation:mcd-spin .7s linear infinite;flex:none}' +
      '.mcd-tnm{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--d-acc);' +
        'font-weight:500;white-space:nowrap}' +
      '.mcd-targ{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--d-dim);' +
        'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:380px}' +
      '.mcd-tst{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--d-dim);' +
        'margin-left:auto;flex:none;white-space:nowrap}' +
      '.mcd-tbody{padding:9px 12px;display:flex;flex-direction:column;gap:6px}' +
      // results
      '.mcd-res{display:flex;align-items:flex-start;gap:9px;padding:8px 11px;border:1px solid var(--d-brd);' +
        'border-radius:7px;background:var(--d-bg2)}' +
      '.mcd-ref{font-family:"JetBrains Mono",monospace;font-size:11px;font-weight:600;color:var(--d-acc);' +
        'background:var(--d-abg);border-radius:4px;padding:2px 6px;flex:none;white-space:nowrap}' +
      '.mcd-rpass{font-size:13px;line-height:1.45;color:var(--d-fg2);font-style:italic}' +
      // stats
      '.mcd-srow{display:flex;align-items:center;gap:8px;padding:5px 2px}' +
      '.mcd-slbl{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--d-dim);flex:1}' +
      '.mcd-sval{font-family:"JetBrains Mono",monospace;font-size:13px;font-weight:600;' +
        'color:var(--d-fg2);white-space:nowrap}' +
      '.mcd-sval.big{color:var(--d-acc);font-size:17px}' +
      // definition
      '.mcd-defbox{padding:10px 12px}' +
      '.mcd-defword{font-family:"JetBrains Mono",monospace;font-size:15px;font-weight:600;' +
        'color:var(--d-acc);margin-bottom:2px}' +
      '.mcd-defgram{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--d-dim);margin-bottom:6px}' +
      '.mcd-deftxt{font-size:13px;line-height:1.55;color:var(--d-fg2);font-style:italic}' +
      '.mcd-defsrcs{display:flex;gap:5px;margin-top:6px}' +
      '.mcd-srctag{font-family:"JetBrains Mono",monospace;font-size:10px;background:var(--d-abg);' +
        'color:var(--d-acc);border-radius:4px;padding:2px 6px}' +
      'a.mcd-srctag{text-decoration:none;cursor:pointer;transition:opacity .15s}' +
      'a.mcd-srctag:hover{opacity:.7}' +
      '.mcd-defetym{font-size:11.5px;color:var(--d-fg2);margin-bottom:10px;padding-bottom:8px;' +
        'border-bottom:1px solid var(--d-brd);line-height:1.5}' +
      '.mcd-defsense{display:flex;gap:8px;margin-bottom:6px;align-items:baseline}' +
      '.mcd-sensn{font-family:"JetBrains Mono",monospace;font-size:10px;color:var(--d-acc);flex:none;min-width:14px}' +
      '.mcd-senslbl{font-family:"JetBrains Mono",monospace;font-size:10px;color:var(--d-dim);' +
        'text-transform:uppercase;letter-spacing:.04em;flex:none;min-width:68px}' +
      '.mcd-senstxt{font-size:12.5px;line-height:1.5;color:var(--d-fg2);font-style:italic}' +
      '.mcd-defnote{font-size:11.5px;color:var(--d-dim);font-style:italic;margin-top:8px;' +
        'padding-top:8px;border-top:1px solid var(--d-brd);line-height:1.45}' +
      // translation pairs
      '.mcd-pair{padding:8px 11px;border:1px solid var(--d-brd);border-radius:7px}' +
      '.mcd-plbl{font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.07em;' +
        'text-transform:uppercase;color:var(--d-dim);margin-bottom:4px}' +
      '.mcd-ptxt{font-size:13px;line-height:1.5;color:var(--d-fg2);font-style:italic}' +
      // outline
      '.mcd-orow{display:flex;align-items:center;gap:9px;padding:6px 3px;' +
        'border-bottom:1px solid var(--d-brd)}' +
      '.mcd-orow:last-of-type{border-bottom:none}' +
      '.mcd-orange{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--d-acc);' +
        'width:44px;flex:none}' +
      '.mcd-otitle{font-size:13px;color:var(--d-fg2);flex:1}' +
      '.mcd-osub{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--d-dim);flex:none}' +
      '.mcd-ometa{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--d-dim);' +
        'padding:6px 3px 0;margin-top:2px;border-top:1px solid var(--d-brd)}' +
      // baskets
      '.mcd-brow{display:flex;align-items:baseline;gap:10px;padding:7px 3px}' +
      '.mcd-bname{font-size:13px;color:var(--d-fg2);flex:1}' +
      '.mcd-bsegs{font-family:"JetBrains Mono",monospace;font-size:12px;font-weight:600;' +
        'color:var(--d-acc);flex:none;white-space:nowrap}' +
      '.mcd-bnote{font-family:"JetBrains Mono",monospace;font-size:10px;color:var(--d-dim);' +
        'flex:none;white-space:nowrap}' +
      '.mcd-btotal{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--d-dim);' +
        'padding:5px 3px 0;margin-top:2px;border-top:1px solid var(--d-brd)}' +
      // narrative
      '.mcd-nsec{margin-bottom:9px}' +
      '.mcd-nhead{font-size:13.5px;font-weight:600;color:var(--d-fg);line-height:1.4;margin-bottom:4px}' +
      '.mcd-nbody{font-size:12.5px;line-height:1.55;color:var(--d-fg2)}' +
      '.mcd-nverse{border-left:2px solid var(--d-acc);padding:5px 10px;margin:4px 0 5px;' +
        'font-size:12px;font-style:italic;color:var(--d-fg2);line-height:1.6;' +
        'background:var(--d-hbg);border-radius:0 4px 4px 0}' +
      // chat response
      '.mcd-chatbox{flex:1;min-height:0;overflow-y:auto;padding:4px 16px 12px;' +
        'scrollbar-width:thin;scrollbar-color:var(--d-brd) transparent}' +
      '.mcd-chatbox::-webkit-scrollbar{width:4px}' +
      '.mcd-chatbox::-webkit-scrollbar-thumb{background:var(--d-brd);border-radius:2px}' +
      '.mcd-cp{font-size:13px;line-height:1.65;color:var(--d-fg2);margin:0 0 10px;letter-spacing:-.01em}' +
      '.mcd-cp em{font-style:italic;color:var(--d-fg)}' +
      '.mcd-ch3{font-size:13.5px;font-weight:600;color:var(--d-fg);margin:16px 0 5px;line-height:1.38}' +
      '.mcd-ch3:first-child{margin-top:2px}' +
      '.mcd-cverse{border-left:2px solid var(--d-acc);padding:7px 12px;margin:4px 0 10px;' +
        'font-size:12.5px;font-style:italic;color:var(--d-fg2);line-height:1.7;' +
        'background:var(--d-hbg);border-radius:0 4px 4px 0}' +
      '.mcd-csrcs{display:flex;gap:6px;flex-wrap:wrap;margin-top:14px;padding-top:10px;' +
        'border-top:1px solid var(--d-brd)}' +
      // chat table
      '.mcd-ctable{display:flex;flex-direction:column;border:1px solid var(--d-brd);border-radius:6px;' +
        'overflow:hidden;margin:4px 0 10px;font-size:12px}' +
      '.mcd-trow{display:grid;grid-template-columns:1.6fr 1.4fr 1.8fr}' +
      '.mcd-trow:not(:last-child){border-bottom:1px solid var(--d-brd)}' +
      '.mcd-trow span{padding:5px 9px;color:var(--d-fg2);line-height:1.4}' +
      '.mcd-thr span{font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.04em;' +
        'text-transform:uppercase;color:var(--d-dim);background:var(--d-bg3)}' +
      '.mcd-tpali{font-style:italic;color:var(--d-fg)!important}' +
      // question nav (arrows + dots)
      '.mcd-qnav{display:flex;align-items:center;justify-content:center;gap:10px;flex:none;padding:7px 0 2px}' +
      '.mcd-narr{width:24px;height:24px;border-radius:5px;border:1px solid var(--d-brd);' +
        'background:transparent;color:var(--d-dim);cursor:pointer;font-size:16px;line-height:1;' +
        'display:flex;align-items:center;justify-content:center;transition:all .15s;padding:0}' +
      '.mcd-narr:hover:not([disabled]){border-color:var(--d-acc);color:var(--d-acc)}' +
      '.mcd-narr[disabled]{opacity:.28;cursor:default}' +
      '.mcd-ndots{display:flex;gap:6px;align-items:center}' +
      '.mcd-dot{width:6px;height:6px;border-radius:50%;background:var(--d-brd2);cursor:pointer;' +
        'transition:all .18s;flex:none}' +
      '.mcd-dot.on{background:var(--d-acc);transform:scale(1.25)}' +
      '.mcd-dot:hover:not(.on){background:var(--d-dim)}' +
      '@keyframes mcd-nudge{0%,55%,100%{transform:translateX(0)}' +
        '60%{transform:translateX(4px);color:var(--d-acc);border-color:var(--d-acc)}' +
        '70%{transform:translateX(0)}' +
        '75%{transform:translateX(3px);color:var(--d-acc);border-color:var(--d-acc)}' +
        '85%{transform:translateX(0)}}' +
      '.mcd-narr-hint{transition:none;animation:mcd-nudge 5s ease 2.5s infinite}' +
      // answer
      '.mcd-spacer{flex:1}' +
      '.mcd-ans{display:flex;gap:10px;align-items:flex-start}' +
      '.mcd-av{width:24px;height:24px;border-radius:6px;background:var(--d-acc);flex:none;' +
        'display:flex;align-items:center;justify-content:center;margin-top:2px}' +
      '.mcd-avd{width:7px;height:7px;border-radius:50%;border:2px solid var(--d-bg2)}' +
      '.mcd-abdy{flex:1}' +
      '.mcd-atxt{font-size:15px;line-height:1.6;color:var(--d-fg);letter-spacing:-.005em;' +
        'white-space:pre-wrap}' +
      '.mcd-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}' +
      '.mcd-chip{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--d-fg2);' +
        'background:var(--d-hbg);border:1px solid var(--d-hbrd);border-radius:5px;' +
        'padding:3px 8px;display:inline-flex;align-items:center;gap:4px}' +
      '.mcd-chip::before{content:"";width:5px;height:5px;border-radius:50%;background:var(--d-grn);display:block}' +
      'a.mcd-chip,a.mcd-chip:visited{text-decoration:none;color:var(--d-fg2)}' +
      'a.mcd-chip{cursor:pointer;transition:border-color .15s,color .15s}' +
      'a.mcd-chip:hover{border-color:var(--d-acc);color:var(--d-acc)}' +
      // fullscreen
      '.mcd-outer:fullscreen{aspect-ratio:unset!important;border-radius:0}' +
      '.mcd-outer:-webkit-full-screen{aspect-ratio:unset!important;border-radius:0}' +
      // mobile mode (toggled via JS class .mcd-mobile when width < 640)
      '.mcd-mobile{aspect-ratio:unset!important;height:auto!important}' +
      '.mcd-mobile .mcd-inner{position:relative!important;top:auto!important;left:auto!important;width:100%!important;height:auto!important;transform:none!important}' +
      '.mcd-mobile .mcd-bg{position:relative!important;inset:unset!important;height:auto!important;flex-direction:column!important}' +
      '.mcd-mobile .mcd-sidebar{width:auto!important;border-right:none!important;border-bottom:1px solid var(--d-brd);padding:10px 14px 8px!important;display:grid!important;grid-template-columns:1fr auto;grid-template-rows:auto auto;column-gap:8px}' +
      '.mcd-mobile .mcd-logo{grid-column:1;grid-row:1;align-self:center}' +
      '.mcd-mobile .mcd-sidebtns{grid-column:2;grid-row:1;align-self:center;margin-top:0!important}' +
      '.mcd-mobile .mcd-tabs{grid-column:1/-1;grid-row:2;flex-direction:row!important;flex-wrap:wrap!important;gap:5px!important;margin-top:6px!important;overflow-y:visible!important}' +
      '.mcd-mobile .mcd-tab{width:auto!important}' +
      '.mcd-mobile .mcd-subtabs{display:none!important}' +
      '.mcd-mobile .mcd-main{padding:10px 14px 16px!important}' +
      '.mcd-mobile .mcd-targ{flex:1!important;min-width:0!important;max-width:none!important}' +
      '.mcd-mobile .mcd-frame{flex:none!important;height:460px;padding:12px 14px!important}' +
      // sutta viewer
      '.mcd-vwr{border:1px solid var(--d-brd);border-radius:6px;overflow:hidden;margin-bottom:10px}' +
      '.mcd-vhdr{padding:5px 10px;border-bottom:1px solid var(--d-brd);font-family:"JetBrains Mono",monospace;font-size:10px;font-weight:600;color:var(--d-fg2);display:flex;justify-content:space-between;align-items:center;background:var(--d-bg3)}' +
      '.mcd-vsegs{max-height:180px;overflow-y:auto;scrollbar-width:none}' +
      '.mcd-vsegs::-webkit-scrollbar{display:none}' +
      '.mcd-vseg{display:grid;grid-template-columns:80px 1fr 1fr;border-bottom:1px solid var(--d-brd)}' +
      '.mcd-vseg:last-child{border-bottom:none}' +
      '.mcd-vseg.hi{background:var(--d-abg)}' +
      '.mcd-sid{font-family:"JetBrains Mono",monospace;font-size:9px;color:var(--d-dim);padding:5px 6px;border-right:1px solid var(--d-brd);line-height:1.4;word-break:break-all}' +
      '.mcd-vseg.hi .mcd-sid{color:var(--d-acc);font-weight:600}' +
      '.mcd-vp{padding:5px 8px;font-style:italic;color:var(--d-fg2);font-size:11px;line-height:1.5;border-right:1px solid var(--d-brd)}' +
      '.mcd-ve{padding:5px 8px;color:var(--d-fg2);font-size:11px;line-height:1.5}' +
      '.mcd-vseg.hi .mcd-vp,.mcd-vseg.hi .mcd-ve{color:var(--d-fg)}';
    document.head.appendChild(el);
  }

  // ── Animation helpers ───────────────────────────────────────────────────────
  function clamp(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function eoCubic(x) { var v = 1 - x; return 1 - v * v * v; }
  function riseR(t, s, d) {
    var e = eoCubic(clamp((t - s) / (d || 0.5)));
    return { o: e.toFixed(3), y: ((1 - e) * 10).toFixed(1) };
  }
  function applyR(el, r) {
    el.style.opacity = r.o;
    el.style.transform = 'translateY(' + r.y + 'px)';
  }
  function streamStr(str, t, s, d) {
    var n = Math.round(clamp((t - s) / (d || 1)) * str.length);
    return str.slice(0, n);
  }
  function svgCheck(c) {
    return '<svg width="13" height="13" viewBox="0 0 14 14" fill="none">' +
      '<path d="M2.5 7.5l3 3 6-7" stroke="' + c + '" stroke-width="2"' +
      ' stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }
  var FS_ON  = '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 1H1V4.5M7.5 1H11V4.5M11 7.5V11H7.5M1 7.5V11H4.5"/></svg>';
  var FS_OFF = '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 1V4.5H1M7.5 1V4.5H11M7.5 11V7.5H11M4.5 11V7.5H1"/></svg>';

  // ── McpDemo ─────────────────────────────────────────────────────────────────
  function McpDemo(container) {
    this.el = container;
    this.theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    this.tab = 0;
    this.sceneStart = Date.now();
    this._timer = null;
    this._ro = null;
    this._anims = [];
    this._chipEls = [];
    this.scIdx = 0;
    this._builtTab = -1;
    this._builtScIdx = -1;
    this._chatEl = null;
    this._spacerEl = null;
    this._scrollLocked = false;
    this._d = null;
  }

  McpDemo.prototype.mount = function () {
    injectCSS();
    this._buildDOM();
    this._applyTheme();
    this._updateQNav();
    this.sceneStart = Date.now();
    this._timer = setInterval(this._tick.bind(this), 33);
    var self = this;
    if (typeof ResizeObserver !== 'undefined') {
      var wrap = this.el.querySelector('.mcd-outer');
      var inner = this.el.querySelector('.mcd-inner');
      function resize() {
        var w = wrap.clientWidth;
        if (w >= 640) {
          wrap.classList.remove('mcd-mobile');
          inner.style.transform = 'scale(' + (w / 1280) + ')';
        } else {
          wrap.classList.add('mcd-mobile');
          inner.style.transform = 'none';
        }
      }
      resize();
      this._ro = new ResizeObserver(resize);
      this._ro.observe(wrap);
    }
  };

  McpDemo.prototype.unmount = function () {
    if (this._timer) clearInterval(this._timer);
    if (this._ro) this._ro.disconnect();
  };

  McpDemo.prototype._buildDOM = function () {
    var self = this;
    this.el.innerHTML =
      '<div class="mcd-outer"><div class="mcd-inner"><div class="mcd-bg">' +
      '<div class="mcd-sidebar">' +
        '<div class="mcd-logo"><div class="mcd-ldot"></div>tripiṭaka·mcp</div>' +
        '<div class="mcd-tabs" id="mcd-tabs"></div>' +
        '<div class="mcd-sidebtns">' +
          '<button class="mcd-tbtn" id="mcd-tbtn" title="Toggle light / dark">☀</button>' +
          '<button class="mcd-tbtn" id="mcd-fsbtn" title="Fullscreen">' + FS_ON + '</button>' +
        '</div>' +
      '</div>' +
      '<div class="mcd-main">' +
      '<div class="mcd-frame">' +
        '<div class="mcd-qrow"><div class="mcd-qbub">' +
          '<span id="mcd-qt"></span><span id="mcd-cur" class="mcd-cur"></span>' +
        '</div></div>' +
        '<div id="mcd-tool" class="mcd-tool" style="opacity:0">' +
          '<div class="mcd-thd">' +
            '<span id="mcd-ico"></span>' +
            '<span id="mcd-tnm" class="mcd-tnm"></span>' +
            '<span id="mcd-targ" class="mcd-targ"></span>' +
            '<span id="mcd-tst" class="mcd-tst"></span>' +
          '</div>' +
          '<div id="mcd-tbody" class="mcd-tbody"></div>' +
        '</div>' +
        '<div class="mcd-spacer"></div>' +
        '<div id="mcd-ans" class="mcd-ans" style="opacity:0">' +
          '<div class="mcd-av"><div class="mcd-avd"></div></div>' +
          '<div class="mcd-abdy">' +
            '<div id="mcd-atxt" class="mcd-atxt"></div>' +
            '<div id="mcd-chips" class="mcd-chips"></div>' +
          '</div>' +
        '</div>' +
        '<div id="mcd-qnav" class="mcd-qnav" style="display:none"></div>' +
      '</div>' +
      '</div></div></div></div>';

    // Tab buttons + sub-questions
    var tabsEl = this.el.querySelector('#mcd-tabs');
    TAB_GROUPS.forEach(function (g, i) {
      var btn = document.createElement('button');
      btn.className = 'mcd-tab' + (i === 0 ? ' on' : '');
      btn.textContent = g.tab;
      btn.addEventListener('click', function () { self._goto(i); });
      tabsEl.appendChild(btn);
      var sub = document.createElement('div');
      sub.className = 'mcd-subtabs' + (i === 0 ? ' on' : '');
      g.scenarios.forEach(function (sc, j) {
        var stab = document.createElement('button');
        stab.className = 'mcd-stab' + (j === 0 ? ' on' : '');
        stab.textContent = sc.question;
        stab.addEventListener('click', function () { self._gotoScIdx(i, j); });
        sub.appendChild(stab);
      });
      tabsEl.appendChild(sub);
    });

    // Theme toggle
    this.el.querySelector('#mcd-tbtn').addEventListener('click', function () {
      self.theme = self.theme === 'dark' ? 'light' : 'dark';
      self._applyTheme();
      self.el.querySelector('#mcd-tbtn').textContent = self.theme === 'dark' ? '☀' : '☾';
    });

    // Fullscreen toggle
    var fsBtn = this.el.querySelector('#mcd-fsbtn');
    var outerEl = this.el.querySelector('.mcd-outer');
    fsBtn.addEventListener('click', function () {
      if (!document.fullscreenElement) {
        outerEl.requestFullscreen && outerEl.requestFullscreen().catch(function () {});
      } else {
        document.exitFullscreen && document.exitFullscreen();
      }
    });
    document.addEventListener('fullscreenchange', function () {
      fsBtn.innerHTML = document.fullscreenElement ? FS_OFF : FS_ON;
    });

    this._d = {
      root:   this.el.querySelector('.mcd-outer'),
      bg:     this.el.querySelector('.mcd-bg'),
      tabs:   this.el.querySelectorAll('.mcd-tab'),
      qt:     this.el.querySelector('#mcd-qt'),
      cur:    this.el.querySelector('#mcd-cur'),
      tool:   this.el.querySelector('#mcd-tool'),
      ico:    this.el.querySelector('#mcd-ico'),
      tnm:    this.el.querySelector('#mcd-tnm'),
      targ:   this.el.querySelector('#mcd-targ'),
      tst:    this.el.querySelector('#mcd-tst'),
      tbody:  this.el.querySelector('#mcd-tbody'),
      ans:    this.el.querySelector('#mcd-ans'),
      atxt:   this.el.querySelector('#mcd-atxt'),
      chips:  this.el.querySelector('#mcd-chips'),
      qnav:   this.el.querySelector('#mcd-qnav')
    };
  };

  McpDemo.prototype._applyTheme = function () {
    var tok = this.theme === 'dark' ? DARK : LIGHT;
    var root = this._d && this._d.root;
    if (!root) return;
    for (var k in tok) root.style.setProperty(k, tok[k]);
  };

  McpDemo.prototype._goto = function (idx) {
    this.tab = idx;
    this.scIdx = 0;
    this.sceneStart = Date.now();
    this._builtTab = -1;
    this._builtScIdx = -1;
    var tabs = this._d.tabs;
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].classList.toggle('on', i === idx);
    }
    var subtabs = this.el.querySelectorAll('.mcd-subtabs');
    for (var j = 0; j < subtabs.length; j++) {
      subtabs[j].classList.toggle('on', j === idx);
    }
    this._updateStabs();
    this._updateQNav();
  };

  McpDemo.prototype._gotoQ = function (qIdx) {
    this.scIdx = qIdx;
    this.sceneStart = Date.now();
    this._builtScIdx = -1;
    this._updateStabs();
    this._updateQNav();
  };

  McpDemo.prototype._gotoScIdx = function (tabIdx, scIdx) {
    if (this.tab !== tabIdx) { this._goto(tabIdx); }
    this._gotoQ(scIdx);
  };

  McpDemo.prototype._updateStabs = function () {
    var allSubs = this.el.querySelectorAll('.mcd-subtabs');
    var sub = allSubs[this.tab];
    if (!sub) return;
    var stabs = sub.querySelectorAll('.mcd-stab');
    for (var i = 0; i < stabs.length; i++) {
      stabs[i].classList.toggle('on', i === this.scIdx);
    }
    if (stabs[this.scIdx]) stabs[this.scIdx].scrollIntoView({ block: 'nearest' });
  };

  McpDemo.prototype._updateQNav = function () {
    var group = TAB_GROUPS[this.tab];
    var total = group.scenarios.length;
    var qi = this.scIdx;
    var qnav = this._d.qnav;
    qnav.innerHTML = '';
    if (total <= 1) { qnav.style.display = 'none'; return; }
    qnav.style.display = 'flex';
    var self = this;

    var l = document.createElement('button');
    l.className = 'mcd-narr';
    l.innerHTML = '&#8249;';
    if (qi === 0) l.setAttribute('disabled', '');
    l.addEventListener('click', function () { if (qi > 0) self._gotoQ(qi - 1); });
    qnav.appendChild(l);

    var dots = document.createElement('div');
    dots.className = 'mcd-ndots';
    for (var i = 0; i < total; i++) {
      var dot = document.createElement('span');
      dot.className = 'mcd-dot' + (i === qi ? ' on' : '');
      (function (idx) {
        dot.addEventListener('click', function () { self._gotoQ(idx); });
      })(i);
      dots.appendChild(dot);
    }
    qnav.appendChild(dots);

    var r = document.createElement('button');
    r.className = 'mcd-narr' + (qi < total - 1 ? ' mcd-narr-hint' : '');
    r.innerHTML = '&#8250;';
    if (qi === total - 1) r.setAttribute('disabled', '');
    r.addEventListener('click', function () { if (qi < total - 1) self._gotoQ(qi + 1); });
    qnav.appendChild(r);
  };

  McpDemo.prototype._buildScene = function (scn) {
    this._builtTab = this.tab;
    this._builtScIdx = this.scIdx;
    this._anims = [];
    this._chipEls = [];

    // Clean up chat overlay from previous scene
    if (this._chatEl && this._chatEl.parentNode) {
      this._chatEl.parentNode.removeChild(this._chatEl);
      this._chatEl = null;
    }
    if (this._spacerEl) { this._spacerEl.style.display = ''; this._spacerEl = null; }
    this._scrollLocked = false;
    this._d.ans.style.display = '';

    var body = this._d.tbody;
    var chipsEl = this._d.chips;
    body.innerHTML = '';
    body.style.padding = '';
    chipsEl.innerHTML = '';
    this._d.tool.style.opacity = 0;
    this._d.ans.style.opacity = 0;
    this._d.atxt.textContent = '';
    this._d.qt.textContent = '';
    this._d.cur.style.display = 'none';

    var self = this;
    var base = scn.toolDur + 0.2;

    if (scn.type === 'results') {
      scn.results.forEach(function (r, i) {
        var d = document.createElement('div');
        d.className = 'mcd-res'; d.style.opacity = 0;
        d.innerHTML = '<span class="mcd-ref">' + r.ref + '</span>' +
          '<span class="mcd-rpass">' + r.passage + '</span>';
        body.appendChild(d);
        self._anims.push({ el: d, s: base + i * 0.38, d: 0.44 });
      });

    } else if (scn.type === 'stats') {
      scn.stats.forEach(function (row, i) {
        var d = document.createElement('div');
        d.className = 'mcd-srow'; d.style.opacity = 0;
        d.innerHTML = '<span class="mcd-slbl">' + row.label + '</span>' +
          '<span class="mcd-sval' + (row.big ? ' big' : '') + '">' + row.value + '</span>';
        body.appendChild(d);
        self._anims.push({ el: d, s: base + i * 0.26, d: 0.38 });
      });

    } else if (scn.type === 'def') {
      var db = document.createElement('div');
      db.className = 'mcd-defbox'; db.style.opacity = 0;
      var dInner = '<div class="mcd-defword">' + scn.def.word + '</div>' +
        '<div class="mcd-defgram">' + scn.def.gram + '</div>';
      if (scn.def.etym) dInner += '<div class="mcd-defetym">' + scn.def.etym + '</div>';
      if (scn.def.senses) {
        dInner += scn.def.senses.map(function (s) {
          return '<div class="mcd-defsense">' +
            '<span class="mcd-sensn">' + s.n + '</span>' +
            (s.label ? '<span class="mcd-senslbl">' + s.label + '</span>' : '') +
            '<span class="mcd-senstxt">' + s.text + '</span>' +
            '</div>';
        }).join('');
      } else {
        dInner += '<div class="mcd-deftxt">' + scn.def.text + '</div>';
      }
      if (scn.def.note) dInner += '<div class="mcd-defnote">' + scn.def.note + '</div>';
      dInner += '<div class="mcd-defsrcs">' +
        scn.def.sources.map(function (s) {
          return typeof s === 'object'
            ? '<a class="mcd-srctag" href="' + s.href + '" target="_blank" rel="noopener">' + s.label + '</a>'
            : '<span class="mcd-srctag">' + s + '</span>';
        }).join('') +
      '</div>';
      db.innerHTML = dInner;
      body.appendChild(db);
      this._anims.push({ el: db, s: base, d: 0.55 });

    } else if (scn.type === 'pairs') {
      scn.pairs.forEach(function (p, i) {
        var d = document.createElement('div');
        d.className = 'mcd-pair'; d.style.opacity = 0;
        d.innerHTML = '<div class="mcd-plbl">' + p.label + '</div>' +
          '<div class="mcd-ptxt">' + p.text + '</div>';
        body.appendChild(d);
        self._anims.push({ el: d, s: base + i * 0.52, d: 0.44 });
      });

    } else if (scn.type === 'outline') {
      var owrap = document.createElement('div'); owrap.style.opacity = 0;
      scn.outline.forEach(function (row) {
        var d = document.createElement('div');
        d.className = 'mcd-orow';
        d.innerHTML =
          '<span class="mcd-orange">' + row.range + '</span>' +
          '<span class="mcd-otitle">' + row.title + '</span>' +
          '<span class="mcd-osub">' + row.sub + '</span>';
        owrap.appendChild(d);
      });
      if (scn.meta) {
        var m = document.createElement('div');
        m.className = 'mcd-ometa'; m.textContent = scn.meta;
        owrap.appendChild(m);
      }
      body.appendChild(owrap);
      this._anims.push({ el: owrap, s: base, d: 0.58 });

    } else if (scn.type === 'baskets') {
      var bwrap = document.createElement('div'); bwrap.style.opacity = 0;
      scn.baskets.forEach(function (b) {
        var d = document.createElement('div');
        d.className = 'mcd-brow';
        d.innerHTML =
          '<span class="mcd-bname">' + b.name + '</span>' +
          '<span class="mcd-bsegs">' + b.segs + ' segs</span>' +
          '<span class="mcd-bnote">' + b.note + '</span>';
        bwrap.appendChild(d);
      });
      if (scn.total) {
        var t = document.createElement('div');
        t.className = 'mcd-btotal'; t.textContent = scn.total;
        bwrap.appendChild(t);
      }
      body.appendChild(bwrap);
      this._anims.push({ el: bwrap, s: base, d: 0.52 });

    } else if (scn.type === 'narrative') {
      scn.sections.forEach(function (sec, i) {
        var d = document.createElement('div');
        d.className = 'mcd-nsec'; d.style.opacity = 0;
        var html = '<div class="mcd-nhead">' + sec.heading + '</div>';
        if (sec.verse) {
          html += '<div class="mcd-nverse">' + sec.verse.replace(/\n/g, '<br>') + '</div>';
        }
        if (sec.body) {
          html += '<div class="mcd-nbody">' + sec.body + '</div>';
        }
        d.innerHTML = html;
        body.appendChild(d);
        self._anims.push({ el: d, s: base + i * 0.65, d: 0.48 });
      });

    } else if (scn.type === 'chat') {
      body.style.padding = '0';
      this._d.ans.style.display = 'none'; // hide avatar/empty answer for chat type
      var frame = body.parentElement.parentElement; // tbody → tool → frame
      var spacer = frame.querySelector('.mcd-spacer');
      spacer.style.display = 'none'; // chatbox fills space directly
      this._spacerEl = spacer;
      var ce = document.createElement('div');
      ce.className = 'mcd-chatbox';
      ce.style.opacity = 0;
      ce.innerHTML = scn.html;
      frame.insertBefore(ce, spacer);
      this._chatEl = ce;
      this._anims.push({ el: ce, s: base, d: 0.5 });
      var self2 = this;
      ce.addEventListener('wheel',     function () { self2._scrollLocked = true; }, { passive: true });
      ce.addEventListener('touchmove', function () { self2._scrollLocked = true; }, { passive: true });
    }

    // Chips
    if (scn.chips) {
      scn.chips.forEach(function (label, i) {
        var sp = document.createElement('span');
        sp.className = 'mcd-chip'; sp.textContent = label; sp.style.opacity = 0;
        chipsEl.appendChild(sp);
        self._chipEls.push({ el: sp, s: scn.toolDur + 3.4 + i * 0.2, d: 0.33 });
      });
    }
  };

  McpDemo.prototype._tick = function () {
    var scn = TAB_GROUPS[this.tab].scenarios[this.scIdx];
    var elapsed = (Date.now() - this.sceneStart) / 1000;

    var t = Math.min(elapsed, scn.dur);
    if (this._builtTab !== this.tab || this._builtScIdx !== this.scIdx) this._buildScene(scn);

    var d = this._d;

    // Fade in only — scene holds at end state
    var fIn = clamp(t / 0.38);
    d.bg.style.opacity = fIn.toFixed(3);

    // Question typewriter
    d.qt.textContent = streamStr(scn.question, t, 0.4, 1.9);
    d.cur.style.display = (t > 0.35 && t < 2.45) ? 'inline-block' : 'none';

    // Tool block
    var tr = riseR(t, 2.5, 0.5);
    d.tool.style.opacity = tr.o;
    d.tool.style.transform = 'translateY(' + tr.y + 'px)';

    var done = t > scn.toolDur;
    d.ico.innerHTML = done
      ? svgCheck('var(--d-grn)')
      : '<span class="mcd-spin"></span>';
    d.tnm.textContent = scn.toolName;
    d.targ.textContent = scn.toolArgs ? '(' + scn.toolArgs + ')' : '()';

    var ss = scn.statuses;
    var si = done
      ? ss.length - 1
      : Math.max(0, Math.min(
          ss.length - 2,
          Math.floor(((t - 2.5) / Math.max(0.1, scn.toolDur - 2.5)) * (ss.length - 1))
        ));
    d.tst.textContent = ss[si];

    // Animated body items
    var i, a, r;
    for (i = 0; i < this._anims.length; i++) {
      a = this._anims[i];
      r = riseR(t, a.s, a.d);
      a.el.style.opacity = r.o;
      a.el.style.transform = 'translateY(' + r.y + 'px)';
    }

    // Answer block (hidden for chat type)
    if (scn.type !== 'chat') {
      var ar = riseR(t, scn.toolDur + 1.0, 0.52);
      d.ans.style.opacity = ar.o;
      d.ans.style.transform = 'translateY(' + ar.y + 'px)';
      d.atxt.textContent = streamStr(scn.answer, t, scn.toolDur + 1.4, 2.8);
    }

    // Chips
    for (i = 0; i < this._chipEls.length; i++) {
      a = this._chipEls[i];
      r = riseR(t, a.s, a.d);
      a.el.style.opacity = r.o;
      a.el.style.transform = 'translateY(' + r.y + 'px)';
    }

    // Auto-scroll chat response (cancelled when user scrolls manually)
    if (this._chatEl && !this._scrollLocked) {
      var sc0 = scn.toolDur + 1.5;
      var sc1 = Math.max(1, scn.dur - sc0 - 2.0);
      var scP = eoCubic(clamp((t - sc0) / sc1));
      var maxSc = this._chatEl.scrollHeight - this._chatEl.clientHeight;
      if (maxSc > 0) this._chatEl.scrollTop = Math.round(scP * maxSc);
    }
  };

  // ── Auto-mount ───────────────────────────────────────────────────────────────
  G.McpDemo = McpDemo;

  function autoMount() {
    document.querySelectorAll('[data-mcp-demo]').forEach(function (el) {
      if (!el._mcpDemo) {
        el._mcpDemo = new McpDemo(el);
        el._mcpDemo.mount();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoMount);
  } else {
    autoMount();
  }

})(window);
