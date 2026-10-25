// recipes: theme toggle, search, and cook mode.
// Cook-mode check-offs live only in this browser (localStorage), per recipe.
(function () {
  "use strict";

  function store(key, value) {
    try {
      if (value === undefined) return JSON.parse(localStorage.getItem(key) || "null");
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      return null;
    }
  }

  // Theme
  var toggle = document.querySelector("[data-theme-toggle]");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  // Search on the index
  var search = document.querySelector("[data-search]");
  if (search) {
    var entries = Array.prototype.slice.call(document.querySelectorAll("[data-entry]"));
    var empty = document.querySelector("[data-search-empty]");
    search.addEventListener("input", function () {
      var words = search.value.toLowerCase().split(/\s+/).filter(Boolean);
      var shown = 0;
      entries.forEach(function (li) {
        var text = li.getAttribute("data-text") || "";
        var hit = words.every(function (w) { return text.indexOf(w) !== -1; });
        li.hidden = !hit;
        if (hit) shown++;
      });
      document.querySelectorAll("[data-subcategory]").forEach(function (sub) {
        sub.hidden = !sub.querySelector("[data-entry]:not([hidden])");
      });
      document.querySelectorAll("[data-category]").forEach(function (cat) {
        cat.hidden = !cat.querySelector("[data-entry]:not([hidden])");
      });
      if (empty) empty.hidden = shown !== 0;
    });
  }

  // Shopping list: which recipes you're making lives in this browser only.
  var PLAN = "recipes:plan";
  var BOUGHT = "recipes:bought";
  function plan() { return store(PLAN) || []; }
  function planQuery(items) {
    return items.map(function (p) { return "r=" + encodeURIComponent(p.slug + "@" + p.scale); }).join("&");
  }
  function showCount() {
    var badge = document.querySelector("[data-list-count]");
    if (!badge) return;
    var n = plan().length;
    badge.textContent = n;
    badge.hidden = n === 0;
  }
  showCount();

  var addBtn = document.querySelector("[data-add-to-list]");
  if (addBtn) {
    var slug = document.querySelector("[data-recipe]").getAttribute("data-recipe");
    var markAdded = function () {
      addBtn.textContent = "On your list ✓";
      addBtn.classList.add("is-on");
    };
    if (plan().some(function (p) { return p.slug === slug; })) markAdded();
    addBtn.addEventListener("click", function () {
      var items = plan().filter(function (p) { return p.slug !== slug; });
      items.push({ slug: slug, scale: addBtn.getAttribute("data-scale"), title: addBtn.getAttribute("data-title") });
      store(PLAN, items);
      markAdded();
      showCount();
    });
  }

  if (location.pathname === "/list") {
    var params = new URLSearchParams(location.search);
    var saved = plan();
    if (!params.has("r") && saved.length) {
      location.replace("/list?" + planQuery(saved));
      return;
    }
    var bought = store(BOUGHT) || {};
    var rows = Array.prototype.slice.call(document.querySelectorAll("[data-bought]"));
    var paint = function () {
      rows.forEach(function (b) {
        var on = !!bought[b.getAttribute("data-bought")];
        b.classList.toggle("is-done", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
    };
    rows.forEach(function (b) {
      b.addEventListener("click", function () {
        var k = b.getAttribute("data-bought");
        if (bought[k]) delete bought[k]; else bought[k] = true;
        store(BOUGHT, bought);
        paint();
      });
    });
    paint();
    document.querySelectorAll("[data-plan-remove]").forEach(function (b) {
      b.addEventListener("click", function () {
        var gone = b.getAttribute("data-plan-remove");
        var items = plan().filter(function (p) { return p.slug !== gone; });
        store(PLAN, items);
        location.replace(items.length ? "/list?" + planQuery(items) : "/list");
      });
    });
    var clearPlan = document.querySelector("[data-clear-plan]");
    if (clearPlan) clearPlan.addEventListener("click", function () {
      store(PLAN, null);
      store(BOUGHT, null);
      location.replace("/list");
    });
    var clearBought = document.querySelector("[data-clear-bought]");
    if (clearBought) clearBought.addEventListener("click", function () {
      bought = {};
      store(BOUGHT, null);
      paint();
    });
  }

  // The owner's cook log. /me/* is behind Cloudflare Access: for anyone else the
  // request is redirected to a login page on another origin, fetch fails, and
  // the widget stays hidden.
  var owner = document.querySelector("[data-owner]");
  if (owner) {
    fetch("/me/status?slug=" + encodeURIComponent(owner.getAttribute("data-slug")), {
      credentials: "same-origin",
      redirect: "error",
      headers: { Accept: "application/json" },
    })
      .then(function (res) { return res.ok ? res.json() : Promise.reject(); })
      .then(function (st) {
        var text = st.count === 0
          ? "Untested: never logged"
          : "Made " + st.count + (st.count === 1 ? " time" : " times") + ", last on " + st.last;
        owner.querySelector("[data-owner-status]").textContent = text;
        var d = new Date();
        var local = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
        owner.querySelector("[data-today]").value = local;
        owner.hidden = false;
      })
      .catch(function () {});
  }

  // Offline: once a page has loaded, it keeps working without signal.
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(function () {});
  }

  // Cook mode
  var recipe = document.querySelector("[data-recipe]");
  if (!recipe) return;
  var key = "recipes:cook:" + recipe.getAttribute("data-recipe");
  var done = store(key) || {};
  var buttons = Array.prototype.slice.call(recipe.querySelectorAll("[data-check]"));
  var steps = buttons.filter(function (b) { return b.hasAttribute("data-step"); });
  var ings = buttons.filter(function (b) { return !b.hasAttribute("data-step"); });
  var ingCount = recipe.querySelector("[data-ing-count]");
  var stepLabel = recipe.querySelector("[data-step-label]");

  function render() {
    buttons.forEach(function (b) {
      var on = !!done[b.getAttribute("data-check")];
      b.classList.toggle("is-done", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.classList.remove("is-current");
    });
    var current = null;
    for (var i = 0; i < steps.length; i++) {
      if (!done[steps[i].getAttribute("data-check")]) { current = steps[i]; break; }
    }
    if (current) current.classList.add("is-current");
    recipe.querySelectorAll("[data-seg]").forEach(function (seg) {
      var id = seg.getAttribute("data-seg");
      seg.className = done[id] ? "is-done" : (current && current.getAttribute("data-check") === id ? "is-current" : "");
    });
    if (ingCount) {
      var got = ings.filter(function (b) { return done[b.getAttribute("data-check")]; }).length;
      ingCount.textContent = got + " of " + ings.length + " in";
    }
    if (stepLabel && steps.length) {
      stepLabel.textContent = current ? "Step " + (steps.indexOf(current) + 1) + " of " + steps.length : "Done. Enjoy.";
    }
  }

  buttons.forEach(function (b) {
    b.addEventListener("click", function (ev) {
      if (ev.target.closest("a")) return; // links inside a line still work
      var id = b.getAttribute("data-check");
      if (done[id]) delete done[id]; else done[id] = true;
      store(key, done);
      render();
    });
  });
  var reset = recipe.querySelector("[data-reset]");
  if (reset) {
    reset.addEventListener("click", function () {
      done = {};
      store(key, null);
      render();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
  render();

  // Keep the screen awake while a recipe is open.
  var lock = null;
  function wake() {
    if (!("wakeLock" in navigator) || document.visibilityState !== "visible") return;
    navigator.wakeLock.request("screen").then(function (l) { lock = l; }).catch(function () {});
  }
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && (!lock || lock.released)) wake();
  });
  wake();
})();
