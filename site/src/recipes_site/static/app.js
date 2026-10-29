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
    var byName = document.querySelector("[data-by-name]");
    var byNameCount = document.querySelector("[data-by-name-count]");
    var jump = document.querySelector("[data-jump]");
    search.addEventListener("input", function () {
      var words = search.value.toLowerCase().replace(/,/g, " ").split(/\s+/).filter(Boolean);
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
      // A tag-only search ("#tea") has no ingredient half, so no "By name" either.
      var tagOnly = words.every(function (w) { return w.charAt(0) === "#"; });
      if (byName) byName.hidden = tagOnly;
      if (byNameCount) byNameCount.textContent = shown ? shown + " recipe" + (shown === 1 ? "" : "s") : "none";
      // While searching, the category chips would fill the space above the keyboard.
      if (jump) jump.hidden = words.length > 0;
      if (empty) {
        empty.hidden = !words.length || shown !== 0;
        empty.textContent = tagOnly ? "Nothing has that tag." : "No recipe has “" + search.value.trim() + "” in its name.";
      }
    });
    // A term chip under the box drops that ingredient from the search.
    document.addEventListener("click", function (ev) {
      var chip = ev.target.closest && ev.target.closest("[data-drop-parts]");
      if (!chip) return;
      // The server says which comma-separated parts made this term ("leeks, Leek").
      var drop = chip.getAttribute("data-drop-parts").split(" ");
      search.value = search.value.split(",").filter(function (p, i) {
        return drop.indexOf(String(i)) === -1 && p.trim();
      }).map(function (p) { return p.trim(); }).join(", ");
      // The other chips' part numbers are stale now; the response redraws them.
      document.getElementById("search-terms").innerHTML = "";
      search.dispatchEvent(new Event("input"));
      search.focus();
    });
    // A tag chip links to /?tag=<tag>: start the index showing just that tag.
    var params = new URLSearchParams(location.search);
    var start = params.get("tag") ? "#" + params.get("tag") : params.get("q");
    if (start) {
      search.value = start;
      search.dispatchEvent(new Event("input"));
      // htmx wires the box up on DOMContentLoaded, after this runs.
      if (start.charAt(0) !== "#") {
        document.addEventListener("DOMContentLoaded", function () {
          if (window.htmx) htmx.trigger(search, "search");
        });
      }
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
      var already = plan().some(function (p) { return p.slug === slug; });
      var items = plan().filter(function (p) { return p.slug !== slug; });
      items.push({ slug: slug, scale: addBtn.getAttribute("data-scale"), title: addBtn.getAttribute("data-title") });
      store(PLAN, items);
      markAdded();
      showCount();
      // Count the add (not a re-add at another scale): an anonymous total, no cookie.
      if (!already && navigator.sendBeacon) {
        var body = new FormData();
        body.append("slug", slug);
        navigator.sendBeacon("/count/list", body);
      }
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
      // A step is a div; its number is the button that carries the state.
      (b.hasAttribute("data-step") ? b.querySelector(".num") : b).setAttribute("aria-pressed", on ? "true" : "false");
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
      if (ev.target.closest("a, [data-timer]")) return; // links and timers inside a line still work
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
      clearTimers();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
  render();

  // Timers: a time named in a step ("bake 30–35 minutes") is a button that
  // starts one. A range checks in at its low end, then counts down to its high
  // end. Visual only, no sound or vibration. Timers are saved as start times in
  // this browser, so a reload or a locked phone doesn't lose them.
  var tray = recipe.querySelector("[data-timer-tray]");
  var timerKey = "recipes:timers:" + recipe.getAttribute("data-recipe");
  var timers = store(timerKey) || {};
  var timerBtns = Array.prototype.slice.call(recipe.querySelectorAll("[data-timer]"));
  var ticker = null;
  var shape = "";
  var ICONS = {
    pause: '<path d="M8 5v14M16 5v14"/>',
    play: '<path d="M7 5l12 7-12 7z"/>',
    cancel: '<path d="M6 6l12 12M18 6L6 18"/>'
  };

  function icon(name) {
    return '<svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">' + ICONS[name] + "</svg>";
  }
  function clock(ms) {
    var total = Math.max(0, Math.ceil(ms / 1000));
    var h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60), sec = total % 60;
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    return h ? h + ":" + pad(m) + ":" + pad(sec) : m + ":" + pad(sec);
  }
  function human(seconds) {
    var n, unit;
    if (seconds >= 3600 && seconds % 1800 === 0) { n = seconds / 3600; unit = "hour"; }
    else if (seconds >= 60 && seconds % 30 === 0) { n = seconds / 60; unit = "minute"; }
    else { n = seconds; unit = "second"; }
    var text = n % 1 ? Math.floor(n) + "½" : String(n);
    if (text.indexOf("0½") === 0) text = "½";
    return text + " " + unit + (n > 1 ? "s" : "");
  }
  function save() { store(timerKey, Object.keys(timers).length ? timers : null); }
  function elapsed(t) { return (t.pausedAt || Date.now()) - t.started; }
  function checkAt(t) { return t.low * 1000 + (t.snooze || 0); }
  function doneAt(t) { return Math.max(t.high * 1000, checkAt(t)); }
  function isUp(t) { return elapsed(t) >= checkAt(t); }

  function startTimer(btn) {
    var id = btn.getAttribute("data-timer");
    if (timers[id]) return;
    var step = btn.closest("[data-step]");
    var num = step ? step.querySelector(".num").textContent.trim() : "";
    var what = btn.getAttribute("data-label");
    timers[id] = {
      label: "Step " + num + (what ? " · " + what : ""),
      low: Number(btn.getAttribute("data-low")),
      high: Number(btn.getAttribute("data-high")),
      started: Date.now(),
      pausedAt: null,
      snooze: 0
    };
    save();
    paintTimers();
  }
  function clearTimers() {
    timers = {};
    save();
    paintTimers();
  }

  function row(id, t) {
    var up = isUp(t);
    var el = document.createElement("div");
    el.className = "timer-row" + (up ? " is-up" : "");
    el.setAttribute("data-row", id);
    if (up) el.setAttribute("role", "alert");
    var main = document.createElement("div");
    main.className = "timer-main";
    var lab = document.createElement("div");
    lab.className = "timer-label";
    lab.textContent = t.label;
    var big = document.createElement("div");
    big.className = "timer-clock";
    big.setAttribute("data-clock", "");
    var note = document.createElement("div");
    note.className = "timer-note";
    note.setAttribute("data-note", "");
    main.appendChild(lab);
    main.appendChild(big);
    main.appendChild(note);
    el.appendChild(main);
    if (up) {
      big.textContent = "Check it now";
      var actions = document.createElement("div");
      actions.className = "timer-actions";
      actions.innerHTML = '<button type="button" class="timer-btn is-solid" data-act="done">Done</button>' +
        '<button type="button" class="timer-btn" data-act="snooze">2 more minutes</button>';
      main.appendChild(actions);
    } else {
      var bar = document.createElement("div");
      bar.className = "timer-bar";
      bar.innerHTML = "<i data-bar></i>";
      main.appendChild(bar);
      var paused = !!t.pausedAt;
      var pause = document.createElement("button");
      pause.type = "button";
      pause.className = "timer-icon";
      pause.setAttribute("data-act", paused ? "resume" : "pause");
      pause.setAttribute("aria-label", paused ? "Resume" : "Pause");
      pause.innerHTML = icon(paused ? "play" : "pause");
      var cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "timer-icon is-quiet";
      cancel.setAttribute("data-act", "cancel");
      cancel.setAttribute("aria-label", "Cancel timer");
      cancel.innerHTML = icon("cancel");
      el.appendChild(pause);
      el.appendChild(cancel);
    }
    return el;
  }

  // Rebuild the tray only when a timer starts, stops, pauses or comes up, so a
  // tap never lands on a button that was just replaced; tick() updates the text.
  function paintTimers() {
    var ids = Object.keys(timers);
    var next = ids.map(function (id) { return id + (isUp(timers[id]) ? "u" : "") + (timers[id].pausedAt ? "p" : ""); }).join(",");
    if (next !== shape) {
      shape = next;
      tray.innerHTML = "";
      ids.forEach(function (id) { tray.appendChild(row(id, timers[id])); });
      tray.hidden = !ids.length;
      tick();
      document.body.style.paddingBottom = ids.length ? tray.offsetHeight + 24 + "px" : "";
    } else {
      tick();
    }
    if (ids.length && !ticker) ticker = setInterval(paintTimers, 1000);
    if (!ids.length && ticker) { clearInterval(ticker); ticker = null; }
  }

  function tick() {
    timerBtns.forEach(function (btn) {
      var t = timers[btn.getAttribute("data-timer")];
      var text = btn.querySelector(".timer-text");
      if (!btn.hasAttribute("data-text")) btn.setAttribute("data-text", text.textContent);
      btn.classList.toggle("is-running", !!t && !isUp(t));
      btn.classList.toggle("is-up", !!t && isUp(t));
      text.textContent = !t ? btn.getAttribute("data-text") : isUp(t) ? "Check" : clock(checkAt(t) - elapsed(t));
    });
    Object.keys(timers).forEach(function (id) {
      var t = timers[id];
      var el = tray.querySelector('[data-row="' + id + '"]');
      if (!el) return;
      var note = el.querySelector("[data-note]");
      if (isUp(t)) {
        var more = doneAt(t) - elapsed(t);
        var said = human(t.low);
        note.textContent = (t.snooze ? "Time’s up." : said + (/^(1|½) /.test(said) ? " is up." : " are up.")) +
          (more > 0 ? " The recipe allows up to " + clock(more) + " more." : "");
      } else {
        el.querySelector("[data-clock]").textContent = clock(checkAt(t) - elapsed(t));
        note.textContent = (t.pausedAt ? "Paused. " : "") + "Check at " + human(t.low) +
          (t.high > t.low ? ", done by " + human(t.high) : "");
        el.querySelector("[data-bar]").style.width = Math.min(100, elapsed(t) / checkAt(t) * 100) + "%";
      }
    });
  }

  timerBtns.forEach(function (btn) {
    btn.addEventListener("click", function () { startTimer(btn); });
  });
  if (tray) {
    tray.addEventListener("click", function (ev) {
      var act = ev.target.closest("[data-act]");
      if (!act) return;
      var id = act.closest("[data-row]").getAttribute("data-row");
      var t = timers[id];
      if (!t) return;
      var what = act.getAttribute("data-act");
      if (what === "pause") t.pausedAt = Date.now();
      else if (what === "resume") { t.started += Date.now() - t.pausedAt; t.pausedAt = null; }
      else if (what === "snooze") t.snooze = elapsed(t) + 120000 - t.low * 1000;
      else delete timers[id];
      save();
      paintTimers();
    });
    // Drop saved timers for steps that no longer exist (the recipe was edited).
    Object.keys(timers).forEach(function (id) {
      if (!recipe.querySelector('[data-timer="' + id + '"]')) delete timers[id];
    });
    save();
    paintTimers();
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") paintTimers();
    });
  }

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
