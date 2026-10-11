/* (주)코리아데이터월드 — 공통 스크립트 */
(function () {
  "use strict";

  // CSS 가 "JS 가 살아 있을 때만" 요소를 숨기도록 표시해 둔다.
  document.documentElement.classList.add("js");

  function initDeck(scope) {
    var decks = scope.querySelectorAll(".deck");
    Array.prototype.forEach.call(decks, function (deck) {
      if (deck.dataset.bound === "1") return;
      deck.dataset.bound = "1";

      var root = deck.closest("section") || scope;
      var cards = Array.prototype.slice.call(deck.querySelectorAll(".dcard"));
      var chips = Array.prototype.slice.call(root.querySelectorAll(".chip"));

      function activate(key) {
        cards.forEach(function (c) {
          c.classList.toggle("is-active", c.dataset.key === key);
        });
        chips.forEach(function (ch) {
          ch.setAttribute("aria-pressed", String(ch.dataset.target === key));
        });
      }

      cards.forEach(function (c) {
        c.addEventListener("click", function () { activate(c.dataset.key); });
        c.addEventListener("mouseenter", function () { activate(c.dataset.key); });
        c.addEventListener("focus", function () { activate(c.dataset.key); });
        c.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
            e.preventDefault();
            activate(c.dataset.key);
          }
        });
      });
      chips.forEach(function (ch) {
        ch.addEventListener("click", function () { activate(ch.dataset.target); });
      });
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

  function closeNav() {
    if (!document.body.classList.contains("nav-open")) return;
    document.body.classList.remove("nav-open");
    var btn = document.querySelector(".vpage:not([hidden]) .nav-toggle") ||
              document.querySelector(".nav-toggle");
    if (btn) {
      btn.setAttribute("aria-expanded", "false");
      btn.setAttribute("aria-label", "메뉴 열기");
    }
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" || e.key === "Esc") closeNav();
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

  function init(scope) {
    scope = scope || document;
    initNav(scope);
    initDeck(scope);
    initReveal(scope);
    initHeader();
  }

  window.KDW = { init: init };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { init(); });
  } else {
    init();
  }
})();
