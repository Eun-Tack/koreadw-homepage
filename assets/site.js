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
    Array.prototype.forEach.call(scope.querySelectorAll(".person-cert.is-link, .cred-item.is-link"), function (b) {
      if (b.dataset.bound === "1") return;
      b.dataset.bound = "1";
      b.addEventListener("click", function () { openCert(b); });
    });
  }

  function init(scope) {
    scope = scope || document;
    initNav(scope);
    initDeck(scope);
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
