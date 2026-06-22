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
        '<div class="mcd-csrcs"><span class="mcd-chip">SN 36.6</span><span class="mcd-chip">MN 131</span><span class="mcd-chip">MN 118</span><span class="mcd-chip">MN 10</span></div>',
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
          '<div class="mcd-csrcs"><span class="mcd-chip">SN 56.11</span><span class="mcd-chip">DN 33</span></div>',
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
          '<div class="mcd-csrcs"><span class="mcd-chip">SN 56.11</span><span class="mcd-chip">AN 4.62</span><span class="mcd-chip">MN 66</span><span class="mcd-chip">SN 45.8</span><span class="mcd-chip">Dhp 204</span></div>',
        answer: ''
      }
      ]  // end search_hybrid.scenarios
    },
    {
      tab: 'survey_corpus',
      scenarios: [{
        question: 'How many times does appamāda appear across the entire Pāli canon?',
        toolName: 'survey_corpus',
        toolArgs: '"appamāda", match_scope="stem"',
        statuses: ['counting segments…', 'tallying pitakas…', '187 segments found'],
        toolDur: 3.2,
        dur: 14,
        type: 'stats',
        stats: [
          { label: 'Total segments',  value: '187',                          big: true },
          { label: 'Distinct suttas', value: '95' },
          { label: 'Sutta Piṭaka',   value: '186' },
          { label: 'Vinaya Piṭaka',  value: '1' },
          { label: 'Word forms',     value: 'appamāda, appamādena, appamādaṃ…' }
        ],
        answer: 'appamāda — "heedfulness / non-negligence" — appears 187 times across 95 suttas. These were the Buddha\'s last words: "All conditioned things are impermanent — strive on with heedfulness." (DN 16:6.1)'
      }]
    },
    {
      tab: 'get_word_definition',
      scenarios: [{
        question: 'What does the word jhāna mean? Show the dictionary definition.',
        toolName: 'get_word_definition',
        toolArgs: '"jhāna"',
        statuses: ['looking up…', 'PTS + Payutto found'],
        toolDur: 2.5,
        dur: 13,
        type: 'def',
        def: {
          word: 'jhāna',
          gram: 'nt.',
          text: 'Meditation, contemplation — the four meditative absorptions. A state of alert mental stillness, not trance; characterised as enhanced vitality rather than mental suppression. The four jhānas are the direct basis for liberating insight.',
          sources: ['PTS Dictionary', 'Payutto']
        },
        answer: 'jhāna = the four meditative absorptions — states of deep, unified attention. The PTS dictionary emphasises: not trance, but "enhanced vitality." The path to Nibbāna runs through all four.'
      }]
    },
    {
      tab: 'compare_translations',
      scenarios: [{
        question: 'Compare Pāli and English in SN 56.11 — the First Discourse.',
        toolName: 'compare_translations',
        toolArgs: '"sn56.11:5.1"',
        statuses: ['fetching editions…', '2 editions aligned'],
        toolDur: 2.8,
        dur: 14,
        type: 'pairs',
        pairs: [
          { label: 'Pāli (canonical)', text: 'Idaṃ kho pana, bhikkhave, dukkhaṃ ariyasaccaṃ: jātipi dukkhā, jarāpi dukkhā, maraṇampi dukkhaṃ…' },
          { label: 'Sujato (EN)',      text: 'Now this is the noble truth of suffering: rebirth is suffering, old age is suffering, death is suffering…' }
        ],
        answer: 'SN 56.11:5.1 — the First Noble Truth as a list. Sujato renders dukkha as "suffering" and preserves the enumerated structure closely. No additional editions are indexed for this segment.'
      }]
    },
    {
      tab: 'get_sutta',
      scenarios: [{
        question: 'Show me the structure of the Ānāpānassati Sutta (MN 118).',
        toolName: 'get_sutta',
        toolArgs: '"mn118", mode="outline"',
        statuses: ['fetching outline…', '44 sections loaded'],
        toolDur: 2.6,
        dur: 13,
        type: 'outline',
        outline: [
          { range: '§1–4',   title: 'First tetrad — mindfulness of body',     sub: '4 steps' },
          { range: '§5–8',   title: 'Second tetrad — mindfulness of feelings', sub: '4 steps' },
          { range: '§9–12',  title: 'Third tetrad — mindfulness of mind',      sub: '4 steps' },
          { range: '§13–16', title: 'Fourth tetrad — mindfulness of phenomena',sub: '4 steps' }
        ],
        meta: '44 sections · 154 segments total',
        answer: 'MN 118 has 44 sections and 154 segments. It maps ānāpānasati onto the four satipaṭṭhānas via four tetrads — a structural key unifying the entire meditation path.'
      }]
    },
    {
      tab: 'list_structure',
      scenarios: [{
        question: 'How is the Pāli Canon structured? What is the full coverage?',
        toolName: 'list_structure',
        toolArgs: '',
        statuses: ['querying…', 'structure loaded'],
        toolDur: 2.0,
        dur: 12,
        type: 'baskets',
        baskets: [
          { name: 'Sutta Piṭaka',      segs: '284,702', note: 'DN · MN · SN · AN · KN' },
          { name: 'Abhidhamma Piṭaka', segs: '88,414',  note: '7 books — Pāli only' },
          { name: 'Vinaya Piṭaka',     segs: '71,557',  note: 'Monks · Nuns · Khandhaka · Parivāra' }
        ],
        total: '≈ 444,673 segments — at parity with SuttaCentral bilara-data',
        answer: 'The three piṭakas cover ~444,673 segments: Sutta (284K), Abhidhamma (88K), and Vinaya (71K). All text is indexed and embedded. Sujato EN + Brahmali EN included.'
      }]
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
      '.mcd-bg{position:absolute;inset:0;background:var(--d-bg);display:flex;flex-direction:column;' +
        'padding:24px 32px 28px;box-sizing:border-box;font-family:system-ui,sans-serif}' +
      '.mcd-hd{display:flex;align-items:center;gap:12px;flex:none;margin-bottom:12px}' +
      '.mcd-logo{font-family:"JetBrains Mono",monospace;font-size:13px;font-weight:600;color:var(--d-fg);' +
        'display:flex;align-items:center;gap:8px;flex:none;white-space:nowrap}' +
      '.mcd-ldot{width:7px;height:7px;border-radius:50%;background:var(--d-grn);' +
        'box-shadow:0 0 0 3px rgba(123,189,142,.16)}' +
      '.mcd-tabs{display:flex;gap:5px;flex:1;overflow:hidden}' +
      '.mcd-tab{font-family:"JetBrains Mono",monospace;font-size:11px;font-weight:500;' +
        'padding:4px 10px;border-radius:5px;border:1px solid var(--d-brd);background:transparent;' +
        'color:var(--d-dim);cursor:pointer;white-space:nowrap;transition:all .15s}' +
      '.mcd-tab.on{background:var(--d-abg);border-color:var(--d-acc);color:var(--d-acc)}' +
      '.mcd-tab:hover:not(.on){border-color:var(--d-brd2);color:var(--d-fg2)}' +
      '.mcd-tbtn{width:28px;height:28px;border-radius:6px;border:1px solid var(--d-brd);' +
        'background:transparent;color:var(--d-dim);cursor:pointer;flex:none;' +
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
      '.mcd-chip::before{content:"";width:5px;height:5px;border-radius:50%;background:var(--d-grn);display:block}';
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
        inner.style.transform = 'scale(' + (wrap.clientWidth / 1280) + ')';
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
      '<div class="mcd-hd">' +
        '<div class="mcd-logo"><div class="mcd-ldot"></div>tripiṭaka·mcp</div>' +
        '<div class="mcd-tabs" id="mcd-tabs"></div>' +
        '<button class="mcd-tbtn" id="mcd-tbtn" title="Toggle light / dark">☀</button>' +
      '</div>' +
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
      '</div></div></div>';

    // Tab buttons
    var tabsEl = this.el.querySelector('#mcd-tabs');
    TAB_GROUPS.forEach(function (g, i) {
      var btn = document.createElement('button');
      btn.className = 'mcd-tab' + (i === 0 ? ' on' : '');
      btn.textContent = g.tab;
      btn.addEventListener('click', function () { self._goto(i); });
      tabsEl.appendChild(btn);
    });

    // Theme toggle
    this.el.querySelector('#mcd-tbtn').addEventListener('click', function () {
      self.theme = self.theme === 'dark' ? 'light' : 'dark';
      self._applyTheme();
      self.el.querySelector('#mcd-tbtn').textContent = self.theme === 'dark' ? '☀' : '☾';
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
    this._updateQNav();
  };

  McpDemo.prototype._gotoQ = function (qIdx) {
    this.scIdx = qIdx;
    this.sceneStart = Date.now();
    this._builtScIdx = -1;
    this._updateQNav();
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
    r.className = 'mcd-narr';
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
      db.innerHTML =
        '<div class="mcd-defword">' + scn.def.word + '</div>' +
        '<div class="mcd-defgram">' + scn.def.gram + '</div>' +
        '<div class="mcd-deftxt">' + scn.def.text + '</div>' +
        '<div class="mcd-defsrcs">' +
          scn.def.sources.map(function (s) {
            return '<span class="mcd-srctag">' + s + '</span>';
          }).join('') +
        '</div>';
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
