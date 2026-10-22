/* (주)코리아데이터월드 — 공통 스크립트 */
(function () {
  "use strict";

  // CSS 가 "JS 가 살아 있을 때만" 요소를 숨기도록 표시해 둔다.
  document.documentElement.classList.add("js");

  var deckIndex = 0;
  function initDeck(scope) {
    var decks = scope.querySelectorAll(".deck");
    Array.prototype.forEach.call(decks, function (deck) {
      if (deck.dataset.bound === "1") return;
      deck.dataset.bound = "1";

      var root = deck.parentElement;
      var cards = Array.prototype.slice.call(deck.querySelectorAll(".dcard"));
      var chips = Array.prototype.slice.call(root.querySelectorAll(".chip"));

      var prefix = "survey-example-" + (++deckIndex);
      var chipGroup = root.querySelector(".chips");
      chipGroup.setAttribute("role", "tablist");
      chips.forEach(function (ch) {
        ch.setAttribute("role", "tab");
        ch.removeAttribute("aria-pressed");
        ch.id = prefix + "-tab-" + ch.dataset.target;
        ch.setAttribute("aria-controls", prefix + "-panel-" + ch.dataset.target);
      });
      cards.forEach(function (c) {
        c.id = prefix + "-panel-" + c.dataset.key;
        c.setAttribute("role", "tabpanel");
        c.setAttribute("aria-labelledby", prefix + "-tab-" + c.dataset.key);
        c.tabIndex = 0;
      });
      function activate(key) {
        cards.forEach(function (c) {
          var active = c.dataset.key === key;
          c.classList.toggle("is-active", active);
          c.hidden = !active;
        });
        chips.forEach(function (ch) {
          var active = ch.dataset.target === key;
          ch.setAttribute("aria-selected", String(active));
          ch.tabIndex = active ? 0 : -1;
        });
      }
      chips.forEach(function (ch, i) {
        ch.addEventListener("click", function () { activate(ch.dataset.target); });
        ch.addEventListener("keydown", function (e) {
          var next;
          if (e.key === "ArrowRight") next = (i + 1) % chips.length;
          else if (e.key === "ArrowLeft") next = (i + chips.length - 1) % chips.length;
          else if (e.key === "Home") next = 0;
          else if (e.key === "End") next = chips.length - 1;
          else return;
          e.preventDefault();
          activate(chips[next].dataset.target);
          chips[next].focus();
        });
      });
      deck.classList.add("is-ready");
      activate("ce");
    });
  }

  function initNav(scope) {
    var toggles = scope.querySelectorAll(".nav-toggle");
    Array.prototype.forEach.call(toggles, function (btn) {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", function () {
        var open = document.body.classList.toggle("nav-open");
        btn.setAttribute("aria-expanded", String(open));
        btn.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
      });
    });

    // 모바일 메뉴에서 링크를 누르면 패널을 닫는다
    var links = scope.querySelectorAll(".nav a");
    Array.prototype.forEach.call(links, function (a) {
      if (a.dataset.bound === "1") return;
      a.dataset.bound = "1";
      a.addEventListener("click", closeNav);
    });
  }

  function closeNav(restoreFocus) {
    if (!document.body.classList.contains("nav-open")) return;
    document.body.classList.remove("nav-open");
    var btn = document.querySelector(".vpage:not([hidden]) .nav-toggle") ||
              document.querySelector(".nav-toggle");
    if (btn) {
      btn.setAttribute("aria-expanded", "false");
      btn.setAttribute("aria-label", "메뉴 열기");
      if (restoreFocus === true) btn.focus();
    }
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" || e.key === "Esc") { closeNav(true); closeCert(); }
  });
  window.addEventListener("resize", function () {
    if (window.innerWidth > 1040) closeNav();
  });

  /* ---------- 스크롤 등장 ----------
     .reveal 요소가 화면에 들어오면 한 번만 나타난다.
     .reveal-group 안에서는 순서대로 조금씩 늦게 나타나 시선이 흐르게 한다.
     모션을 줄이도록 설정한 방문자에게는 아무 효과도 주지 않는다. */
  var REDUCED = window.matchMedia &&
                window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function initReveal(scope) {
    var items = scope.querySelectorAll(".reveal");
    if (!items.length) return;

    if (REDUCED || !("IntersectionObserver" in window)) {
      Array.prototype.forEach.call(items, function (el) {
        el.classList.add("is-in");
      });
      return;
    }

    Array.prototype.forEach.call(scope.querySelectorAll(".reveal-group"), function (g) {
      Array.prototype.forEach.call(g.querySelectorAll(".reveal"), function (el, i) {
        if (!el.style.getPropertyValue("--d")) {
          el.style.setProperty("--d", Math.min(i, 7) * 70 + "ms");
        }
      });
    });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add("is-in");
        io.unobserve(e.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

    Array.prototype.forEach.call(items, function (el) {
      if (el.dataset.bound === "1") return;
      el.dataset.bound = "1";
      io.observe(el);
    });
  }

  /* ---------- 헤더 ----------
     조금만 내려가도 헤더에 그림자를 줘 본문과 분리한다. */
  function initHeader() {
    if (document.body.dataset.hdrBound === "1") return;
    document.body.dataset.hdrBound = "1";
    var tick = false;
    function onScroll() {
      if (tick) return;
      tick = true;
      window.requestAnimationFrame(function () {
        document.body.classList.toggle("is-scrolled", window.scrollY > 12);
        tick = false;
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ---------- 자격증 보기 ----------
     자격증 배지를 누르면 원본 이미지를 띄운다.
     ESC 와 바깥 클릭으로 닫히고, 닫은 뒤 누른 버튼으로 초점을 돌려준다. */
  var certLast = null;

  function certBox() {
    var box = document.getElementById("certview");
    if (box) return box;
    box = document.createElement("div");
    box.id = "certview";
    box.className = "certview";
    box.hidden = true;
    box.innerHTML =
      '<div class="certview-dim" data-close="1"></div>' +
      '<div class="certview-panel" role="dialog" aria-modal="true" aria-label="자격증">' +
      '<p class="certview-title"></p>' +
      '<img class="certview-img" alt="">' +
      '<button type="button" class="certview-close" data-close="1">닫기</button>' +
      "</div>";
    document.body.appendChild(box);
    box.addEventListener("click", function (e) {
      if (e.target.dataset.close) closeCert();
    });
    return box;
  }

  function openCert(btn) {
    var box = certBox();
    var img = box.querySelector(".certview-img");
    img.src = btn.dataset.cert;
    img.alt = btn.dataset.certLabel || "자격증";
    box.querySelector(".certview-title").textContent = btn.dataset.certLabel || "";
    box.hidden = false;
    document.body.classList.add("certview-open");
    certLast = btn;
    box.querySelector(".certview-close").focus();
  }

  function closeCert() {
    var box = document.getElementById("certview");
    if (!box || box.hidden) return;
    box.hidden = true;
    document.body.classList.remove("certview-open");
    if (certLast) { certLast.focus(); certLast = null; }
  }

  function initCert(scope) {
    Array.prototype.forEach.call(scope.querySelectorAll(".person-cert.is-link, .tl-item.is-link, .news-card.is-link"), function (b) {
      if (b.dataset.bound === "1") return;
      b.dataset.bound = "1";
      b.addEventListener("click", function () { openCert(b); });
    });
  }

  /* ---------- 주요 클라이언트 ----------
     그룹 제목 옆의 기관 수를 직접 센다. 한 곳을 더하거나 뺐을 때
     숫자를 같이 고치지 않아 어긋나는 일이 없도록. */
  function initClients(scope) {
    Array.prototype.forEach.call(scope.querySelectorAll(".client-group"), function (g) {
      var n = g.querySelectorAll(".client-grid > li").length;
      var slot = g.querySelector(".client-group-title span");
      if (slot && n) slot.textContent = String(n);
    });
  }

  /* ---------- 연혁 ----------
     화면에 들어 있는 글은 '연도'와 '한 줄짜리 항목'뿐이다.

         <h4>2026</h4>
         <p>10.12 [협약] 한국보훈진흥회 업무협약 체결 | 설명 | 사진파일</p>

     고객이 관리자에서 이 한 줄만 더하면 되도록, 배지 · 세로 줄기 · 분류
     버튼은 여기서 만든다. 분류 머리표는 공지사항 제목에 쓰는 [소식] 과
     같은 방식이라 따로 익힐 것이 없다. */
  var TL_LABEL = {
    "인증": "인증 · 선정", "협약": "협약 · 위촉",
    "언론": "언론 보도", "활동": "대외 활동", "사내": "사내"
  };
  var TL_ORDER = ["인증", "협약", "언론", "활동", "사내"];

  /* 고객이 '10.12' '10월 12일' '2026.10.12' 어떻게 쓰든 화면에는 '10.12' 로
     보이게 맞춘다. 날짜칸이 좁아 긴 표기는 두 줄로 접히기 때문이다.
     숫자가 없으면(예: '상시') 쓴 그대로 둔다. */
  function tlDate(s) {
    var n = s.match(/\d+/g);
    if (!n || !n.length) return s.trim();
    if (n.length >= 3 && n[0].length === 4) n = n.slice(1);   // 연도는 버린다
    function p(x) { return x.length < 2 ? "0" + x : x; }
    if (n.length >= 2) return p(n[0]) + "." + p(n[1]);
    return p(n[0]);
  }

  function buildTimeline(tl) {
    if (tl.dataset.built === "1") return;
    var base = tl.dataset.certBase || "";
    var kids = Array.prototype.slice.call(tl.children);
    if (!kids.length || kids[0].tagName !== "H4") return;

    var years = [], cur = null, seen = {};
    kids.forEach(function (el) {
      if (el.tagName === "H4") {
        cur = { year: el.textContent.trim(), items: [] };
        years.push(cur);
        return;
      }
      if (!cur || el.tagName !== "P") return;
      var raw = el.textContent.trim();
      if (!raw) return;
      var parts = raw.split("|");
      var head = parts[0].trim();

      /* 날짜는 분류 대괄호 앞의 전부로 본다. 고객이 기존 홈페이지에서
         '06월 01일' 처럼 써 왔기 때문에 '10.12' 만 받으면 깨진다. */
      var when, kind, title;
      var m = head.match(/^\s*([\s\S]*?)\s*\[\s*([^\]]+?)\s*\]\s*([\s\S]*)$/);
      if (m) {
        when = m[1]; kind = m[2]; title = m[3];
        if (!TL_LABEL[kind]) {          // 모르는 분류면 글자를 버리지 않는다
          title = "[" + kind + "] " + title;
          kind = "사내";
        }
      } else {
        var m2 = head.match(/^\s*(\S+)\s+([\s\S]*)$/);
        when = m2 ? m2[1] : "";
        title = m2 ? m2[2] : head;
        kind = "사내";
      }
      cur.items.push({
        when: tlDate(when), kind: kind, title: title.trim(),
        desc: (parts[1] || "").trim(), img: (parts[2] || "").trim()
      });
      seen[kind] = 1;
    });
    if (!years.length) return;

    function esc(s) {
      return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
    var html = "";
    years.forEach(function (y) {
      html += '<section class="tl-year reveal" data-year="' + esc(y.year) + '">'
            + '<h3 class="tl-y"><b>' + esc(y.year) + "</b><i>년</i></h3><ul>";
      y.items.forEach(function (it) {
        var body = '<span class="tl-title">' + esc(it.title) + "</span>"
                 + (it.desc ? '<span class="tl-desc">' + esc(it.desc) + "</span>" : "");
        var inner = it.img
          ? '<button type="button" class="tl-item is-link" data-cert="'
            + esc(base + it.img) + '" data-cert-label="' + esc(it.title) + '">' + body + "</button>"
          : '<span class="tl-item">' + body + "</span>";
        html += '<li data-kind="' + esc(it.kind) + '">'
              + '<span class="tl-when">' + esc(it.when) + "</span>"
              + '<span class="tl-kind k-' + esc(it.kind) + '">' + esc(TL_LABEL[it.kind]) + "</span>"
              + inner + "</li>";
      });
      html += "</ul></section>";
    });
    tl.innerHTML = html;
    tl.classList.add("reveal-group");
    tl.dataset.built = "1";

    var bar = document.createElement("div");
    bar.className = "tl-filter";
    bar.setAttribute("role", "group");
    bar.setAttribute("aria-label", "분류별 보기");
    var chips = '<button type="button" class="tl-chip is-on" data-kind="all" aria-pressed="true">전체</button>';
    TL_ORDER.forEach(function (k) {
      if (seen[k]) {
        chips += '<button type="button" class="tl-chip" data-kind="' + k
               + '" aria-pressed="false">' + TL_LABEL[k] + "</button>";
      }
    });
    bar.innerHTML = chips;
    tl.parentNode.insertBefore(bar, tl);
  }

  /* 분류 버튼을 누르면 해당 항목만 남긴다. 항목이 없는 연도는 통째로 감춘다. */
  function initTimeline(scope) {
    Array.prototype.forEach.call(scope.querySelectorAll("[data-timeline]"), buildTimeline);
    Array.prototype.forEach.call(scope.querySelectorAll("[data-timeline]"), function (tl) {
      var bar = tl.parentElement.querySelector(".tl-filter");
      if (!bar || bar.dataset.bound === "1") return;
      bar.dataset.bound = "1";
      var chips = Array.prototype.slice.call(bar.querySelectorAll(".tl-chip"));

      function apply(kind) {
        chips.forEach(function (c) {
          var on = c.dataset.kind === kind;
          c.classList.toggle("is-on", on);
          c.setAttribute("aria-pressed", String(on));
        });
        Array.prototype.forEach.call(tl.querySelectorAll(".tl-year"), function (y) {
          var shown = 0;
          Array.prototype.forEach.call(y.querySelectorAll("li"), function (li) {
            var on = kind === "all" || li.dataset.kind === kind;
            li.hidden = !on;
            if (on) shown++;
          });
          y.hidden = shown === 0;
        });
      }
      chips.forEach(function (c) {
        c.addEventListener("click", function () { apply(c.dataset.kind); });
      });
    });
  }

  function init(scope) {
    scope = scope || document;
    initNav(scope);
    initDeck(scope);
    // 연혁은 글줄에서 화면을 먼저 만들어 둔다.
    // 그래야 리빌 관찰과 자격증 팝업이 새로 생긴 요소까지 집는다.
    initTimeline(scope);
    initClients(scope);
    initReveal(scope);
    initHeader();
    initCert(scope);
    // Keep the current subsection visible without moving the vertical scroll.
    Array.prototype.forEach.call(scope.querySelectorAll(".lnb-in"), function (nav) {
      if (!nav.offsetWidth) return;
      var current = nav.querySelector(".is-active");
      if (current) nav.scrollLeft = current.offsetLeft - (nav.clientWidth - current.offsetWidth) / 2;
      if (nav.dataset.bound === "1") return;
      nav.dataset.bound = "1";
      var controls = nav.parentElement.querySelectorAll(".lnb-scroll");
      function updateControls() {
        Array.prototype.forEach.call(controls, function (btn) {
          btn.disabled = Number(btn.dataset.direction) < 0
            ? nav.scrollLeft <= 1 : nav.scrollLeft + nav.clientWidth >= nav.scrollWidth - 1;
        });
      }
      Array.prototype.forEach.call(controls, function (btn) {
        btn.addEventListener("click", function () {
          nav.scrollBy({left: Number(btn.dataset.direction) * nav.clientWidth * .75, behavior:"smooth"});
        });
      });
      nav.addEventListener("scroll", updateControls, {passive:true});
      if (window.ResizeObserver) new ResizeObserver(updateControls).observe(nav);
      updateControls();
    });
  }

  window.KDW = { init: init };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { init(); });
  } else {
    init();
  }
})();

/* 공지 목록 검색.
   시연 사이트에는 서버가 없으므로 화면에 있는 목록을 걸러 보여 준다.
   후이즈 게시판에서는 같은 자리의 검색창이 서버로 넘어가므로(input 에
   name="ss" 가 붙어 있다) 그때는 끼어들지 않는다. */
(function () {
  var form = document.querySelector(".board-search");
  if (!form) return;
  var box = form.querySelector("input[type=text]");
  if (!box || box.getAttribute("name")) return;

  var list = document.querySelector(".notice-list");
  var pager = document.querySelector(".board-pager");
  if (!list) return;
  var items = [].slice.call(list.children);

  function apply() {
    var q = box.value.trim().toLowerCase();
    var hit = 0;
    for (var i = 0; i < items.length; i++) {
      var on = !q || items[i].textContent.toLowerCase().indexOf(q) >= 0;
      items[i].style.display = on ? "" : "none";
      if (on) hit++;
    }
    if (pager) pager.style.visibility = q ? "hidden" : "";
    var none = list.querySelector(".notice-none");
    if (!hit && !none) {
      none = document.createElement("li");
      none.className = "notice-none";
      none.innerHTML = '<span class="notice-title">찾으시는 글이 없습니다.</span>';
      list.appendChild(none);
    } else if (none) {
      none.style.display = hit ? "none" : "";
    }
  }

  form.addEventListener("submit", function (e) { e.preventDefault(); apply(); });
  box.addEventListener("input", apply);
})();
