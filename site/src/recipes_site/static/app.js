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

  // The menu panel drops in under the header; a tap outside or Escape closes it.
  var toggles = Array.prototype.slice.call(document.querySelectorAll("[data-panel-toggle]"));
  function closePanels(except) {
    toggles.forEach(function (t) {
      var name = t.getAttribute("data-panel-toggle");
      if (name === except) return;
      t.setAttribute("aria-expanded", "false");
      var panel = document.querySelector('[data-panel="' + name + '"]');
      if (panel) panel.hidden = true;
    });
  }
  toggles.forEach(function (t) {
    t.addEventListener("click", function (ev) {
      ev.stopPropagation();
      var name = t.getAttribute("data-panel-toggle");
      var panel = document.querySelector('[data-panel="' + name + '"]');
      var open = panel.hidden;
      closePanels(name);
      panel.hidden = !open;
      t.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });
  // The person popover (the fleet's settings-gear pattern, cocktails#249).
  var personBtn = document.getElementById("person");
  var pop = document.getElementById("person-pop");
  function setPop(open) {
    if (!pop) return;
    pop.classList.toggle("is-open", open);
    personBtn.setAttribute("aria-expanded", String(open));
  }
  if (personBtn && pop) {
    personBtn.addEventListener("click", function (ev) {
      ev.stopPropagation();
      closePanels(null);
      setPop(!pop.classList.contains("is-open"));
    });
  }
  // Opening the menu closes the popover.
  toggles.forEach(function (t) { t.addEventListener("click", function () { setPop(false); }); });

  document.addEventListener("click", function (ev) {
    if (!ev.target.closest("[data-panel]")) closePanels(null);
    if (pop && !pop.contains(ev.target)) setPop(false);
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") { closePanels(null); setPop(false); }
  });

  // Dark mode pill: 🌻 parked left in light, 🌘 slid right in dark.
  var pill = document.getElementById("theme-pill");
  function syncPill() {
    if (!pill) return;
    var dark = document.documentElement.dataset.theme === "dark";
    pill.classList.toggle("is-dark", dark);
    pill.setAttribute("aria-checked", dark ? "true" : "false");
  }
  if (pill) {
    pill.addEventListener("click", function () {
      var next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) {}
      syncPill();
    });
  }
  syncPill();

  // htmx requests echo the double-submit CSRF cookie, which /me/* responses set.
  document.addEventListener("htmx:configRequest", function (ev) {
    var match = document.cookie.match(/(?:^|;\s*)recipes_csrf=([^;]+)/);
    if (match) ev.detail.headers["X-CSRF-Token"] = decodeURIComponent(match[1]);
  });

  // Signed in? /me/* sits behind Cloudflare Access, so for anyone without a
  // current login the request is redirected off-site and fails. Success swaps
  // the outline for the owner's emoji, then (on a recipe page) asks for the
  // cook-log line, so visitors never send that second request.
  var person = document.querySelector("[data-person]");
  var owner = document.querySelector("[data-owner]");
  function signedIn() {
    person.classList.add("is-owner");
    person.querySelector(".person-outline").setAttribute("hidden", "");
    person.querySelector(".person-emoji").hidden = false;
    person.setAttribute("aria-label", "You're signed in: dark mode and your cook log");
    var link = document.querySelector("[data-person-link]");
    if (link) link.textContent = "Cook log";
    if (owner && window.htmx) htmx.trigger(owner, "owner");
  }
  if (person && window.htmx) {
    // After htmx has read its config and wired up the page.
    document.addEventListener("DOMContentLoaded", function () {
      htmx.ajax("GET", "/me/whoami", { source: person, swap: "none" }).catch(function () {});
    });
  }
  document.addEventListener("htmx:afterRequest", function (ev) {
    var elt = ev.detail.elt;
    if (!ev.detail.successful) {
      // htmx doesn't swap an error, so say so rather than leave it looking logged.
      if (elt && elt.hasAttribute && elt.hasAttribute("data-owner-form")) {
        owner.querySelector("[data-owner-status]").textContent = "Not logged: try again";
      }
      return;
    }
    if (person && elt === person) {
      try {
        if (JSON.parse(ev.detail.xhr.responseText).owner) signedIn();
      } catch (e) {}
    } else if (owner && elt === owner) {
      var d = new Date();
      var local = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
      owner.querySelector("[data-today]").value = local;
      owner.hidden = false;
    } else if (elt && elt.hasAttribute && elt.hasAttribute("data-owner-form")) {
      elt.querySelector("[name=note]").value = "";
    }
  });

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
        var tags = (li.getAttribute("data-tags") || "").split(" ");
        // "#tea" matches the tag exactly; any other word matches anywhere.
        var hit = words.every(function (w) {
          return w.charAt(0) === "#" ? tags.indexOf(w.slice(1)) !== -1 : text.indexOf(w) !== -1;
        });
        li.hidden = !hit;
        if (hit) shown++;
      });
      document.querySelectorAll("[data-family]").forEach(function (fam) {
        fam.hidden = !fam.querySelector("[data-entry]:not([hidden])");
      });
      document.querySelectorAll("[data-subcategory]").forEach(function (sub) {
        sub.hidden = !sub.querySelector("[data-entry]:not([hidden])");
      });
      document.querySelectorAll("[data-category]").forEach(function (cat) {
        cat.hidden = !cat.querySelector("[data-entry]:not([hidden])");
      });
      if (empty) empty.hidden = shown !== 0;
    });
    // A tag chip links to /?tag=<tag>: start the index showing just that tag.
    var params = new URLSearchParams(location.search);
    var start = params.get("tag") ? "#" + params.get("tag") : params.get("q");
    if (start) {
      search.value = start;
      search.dispatchEvent(new Event("input"));
    }
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

  // The service worker is gone (offline isn't needed). Drop it, and its caches,
  // from browsers that installed it.
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.getRegistrations().then(function (regs) {
      regs.forEach(function (r) { r.unregister(); });
    }).catch(function () {});
  }
  if ("caches" in window) {
    caches.keys().then(function (keys) {
      keys.filter(function (k) { return k.indexOf("recipes-") === 0; }).forEach(function (k) { caches.delete(k); });
    }).catch(function () {});
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
    // Each part (Dough, Filling, ...) has its own current step: its first open one.
    var currents = {};
    var current = null;
    steps.forEach(function (s) {
      var p = s.getAttribute("data-part");
      if (!done[s.getAttribute("data-check")] && !currents[p]) {
        currents[p] = s;
        s.classList.add("is-current");
        if (!current) current = s;
      }
    });
    var currentIds = {};
    Object.keys(currents).forEach(function (p) { currentIds[currents[p].getAttribute("data-check")] = true; });
    recipe.querySelectorAll("[data-seg]").forEach(function (seg) {
      var id = seg.getAttribute("data-seg");
      seg.className = done[id] ? "is-done" : (currentIds[id] ? "is-current" : "");
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
      if (b.hasAttribute("data-step")) {
        // A step marks where you are in its part: tapping an open step finishes
        // it and everything before it; tapping a finished one reopens it. Either
        // way, everything after it in that part opens again, so a mis-tap undoes
        // in one tap. Other parts are left alone.
        var part = steps.filter(function (s) { return s.getAttribute("data-part") === b.getAttribute("data-part"); });
        var upTo = part.indexOf(b) + (done[id] ? 0 : 1);
        part.forEach(function (s, i) {
          if (i < upTo) done[s.getAttribute("data-check")] = true;
          else delete done[s.getAttribute("data-check")];
        });
      } else if (done[id]) delete done[id]; else done[id] = true;
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
