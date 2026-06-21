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
  var SCENARIOS = [
    {
      tab: 'search_hybrid',
      question: 'What is the Buddha\'s guidance for someone tormented by constant worry?',
      toolName: 'search_hybrid',
      toolArgs: 'query="worry · anxiety · present moment"',
      statuses: ['scanning…', 'matching vectors…', '3 passages found'],
      toolDur: 3.8,
      dur: 17,
      type: 'narrative',
      sections: [
        {
          heading: '1. Most of your pain is a second arrow — and you fired that one yourself.',
          body: 'SN 36.6 — the untrained person, touched by pain, adds mental anguish on top. The trained person feels only the first: "one feeling — physical, not mental." The hours you spend rehearsing the worry in your head are the second arrow — and that one is optional.'
        },
        {
          heading: '2. Worry has no home in the present.',
          verse: "Don't run back to the past,\ndon't anticipate the future.\nWhat's past is left behind;\nthe future has not arrived.",
          body: 'MN 131 — worry is always either re-chewing something finished or pre-living something not yet real. The cure is not to suppress it but to keep seeing the one thing that is real: this present moment.'
        },
        {
          heading: 'The practical anchor — how you actually come back.',
          body: 'MN 118 — when worry pulls the mind into the future, return to the breath: a long breath known as long, a short breath known as short. Not once — thousands of times. That repetition is the practice.'
        }
      ],
      chips: ['SN 36.6', 'MN 131', 'MN 118'],
      answer: 'When the mind is gripped by constant worry, the Buddha\'s guidance isn\'t "force yourself to stop." It\'s to see clearly how the mind manufactures its own suffering, then train it to put the extra weight down.'
    },
    {
      tab: 'survey_corpus',
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
    },
    {
      tab: 'get_word_definition',
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
    },
    {
      tab: 'compare_translations',
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
    },
    {
      tab: 'get_sutta',
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
    },
    {
      tab: 'list_structure',
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
    this._builtTab = -1;
    this._d = null;
  }

  McpDemo.prototype.mount = function () {
    injectCSS();
    this._buildDOM();
    this._applyTheme();
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
      '</div>' +
      '</div></div></div>';

    // Tab buttons
    var tabsEl = this.el.querySelector('#mcd-tabs');
    SCENARIOS.forEach(function (s, i) {
      var btn = document.createElement('button');
      btn.className = 'mcd-tab' + (i === 0 ? ' on' : '');
      btn.textContent = s.tab;
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
      chips:  this.el.querySelector('#mcd-chips')
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
    this.sceneStart = Date.now();
    this._builtTab = -1;
    var tabs = this._d.tabs;
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].classList.toggle('on', i === idx);
    }
  };

  McpDemo.prototype._buildScene = function (scn) {
    this._builtTab = this.tab;
    this._anims = [];
    this._chipEls = [];
    var body = this._d.tbody;
    var chipsEl = this._d.chips;
    body.innerHTML = '';
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
    var scn = SCENARIOS[this.tab];
    var elapsed = (Date.now() - this.sceneStart) / 1000;

    var t = Math.min(elapsed, scn.dur);
    if (this._builtTab !== this.tab) this._buildScene(scn);

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

    // Answer block
    var ar = riseR(t, scn.toolDur + 1.0, 0.52);
    d.ans.style.opacity = ar.o;
    d.ans.style.transform = 'translateY(' + ar.y + 'px)';
    d.atxt.textContent = streamStr(scn.answer, t, scn.toolDur + 1.4, 2.8);

    // Chips
    for (i = 0; i < this._chipEls.length; i++) {
      a = this._chipEls[i];
      r = riseR(t, a.s, a.d);
      a.el.style.opacity = r.o;
      a.el.style.transform = 'translateY(' + r.y + 'px)';
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
