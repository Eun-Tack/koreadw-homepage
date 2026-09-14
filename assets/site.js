/* (주)코리아데이터월드 — 공통 스크립트 */
(function () {
  "use strict";

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

  function init(scope) {
    scope = scope || document;
    initNav(scope);
    initDeck(scope);
  }

  window.KDW = { init: init };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { init(); });
  } else {
    init();
  }
})();
