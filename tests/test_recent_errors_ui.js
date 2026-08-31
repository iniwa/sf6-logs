"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "static", "js", "common.js"), "utf8");

class Element {
    constructor(tagName, id) {
        this.tagName = tagName;
        this.id = id || "";
        this.children = [];
        this.className = "";
        this.style = {};
        this.dataset = {};
        this._textContent = "";
    }

    appendChild(child) {
        this.children.push(child);
        return child;
    }

    remove() {
        this.removed = true;
    }

    get textContent() {
        if (this.children.length) {
            return this.children.map((child) => child.textContent).join("");
        }
        return this._textContent;
    }

    set textContent(value) {
        this._textContent = String(value);
        this.children = [];
    }

    set innerHTML(_) {
        throw new Error("recent-error rendering must use textContent, not innerHTML");
    }
}

function createPage(ids) {
    const elements = new Map();
    for (const id of ids) elements.set(id, new Element("div", id));
    const listeners = {};
    const timers = [];
    const requests = [];
    const responses = [];
    const document = {
        body: new Element("body"),
        getElementById(id) { return elements.get(id) || null; },
        createElement(tagName) { return new Element(tagName); },
        addEventListener(name, callback) { listeners[name] = callback; },
    };
    const context = {
        console,
        document,
        Intl,
        Date,
        Array,
        String,
        isNaN,
        localStorage: {
            getItem() { return null; },
            setItem() {},
        },
        fetch(url) {
            requests.push(url);
            const response = responses.shift() || { scheduler: {}, authenticated: false, mock_mode: false };
            return Promise.resolve({ json: () => Promise.resolve(response) });
        },
        setTimeout() { return 1; },
        setInterval(callback, delay) {
            timers.push({ callback, delay });
            return timers.length;
        },
    };
    context.globalThis = context;
    vm.runInNewContext(source, context, { filename: "common.js" });
    return { context, elements, listeners, timers, requests, responses };
}

function tableRows(list) {
    assert.equal(list.children.length, 1);
    const table = list.children[0];
    assert.equal(table.tagName, "table");
    const body = table.children[1];
    return body.children;
}

async function flush() {
    await new Promise((resolve) => setImmediate(resolve));
}

async function main() {
    const page = createPage(["recent-errors-list", "cfn-badge", "mock-badge"]);
    const list = page.elements.get("recent-errors-list");

    page.context.updateRecentErrors([]);
    assert.match(list.textContent, /エラー履歴はありません/);

    page.context.updateRecentErrors([
        {
            timestamp: "2026-08-30T15:04:05Z",
            source_label: "戦績取得",
            summary: "応答を確認できませんでした <b>secret</b>",
            kind: "network",
            exception_type: "TimeoutError",
        },
        {
            timestamp: "2026-08-30T15:03:05Z",
            source_label: "認証確認",
            summary: "認証に失敗しました",
            kind: "auth",
            exception_type: "HTTPError",
            status_code: 403,
        },
    ]);
    const rows = tableRows(list);
    assert.equal(rows.length, 2);
    assert.match(rows[0].textContent, /戦績取得/);
    assert.match(rows[0].textContent, /応答を確認できませんでした <b>secret<\/b>/);
    assert.match(rows[0].textContent, /TimeoutError/);
    assert.match(rows[0].textContent, /-/); // no HTTP code is shown when absent
    assert.match(rows[1].textContent, /認証確認/);
    assert.match(rows[1].textContent, /403/);
    assert.equal(list.children[0].innerHTML, undefined, "innerHTML must not be used for history rendering");

    // This assertion intentionally requires the user-visible timezone marker.
    assert.match(rows[0].textContent, /2026\/08\/31 00:04:05 JST/);

    const before = list.textContent;
    page.context.updateRecentErrors(undefined);
    assert.equal(list.textContent, before, "missing legacy history must preserve rendered data");

    page.responses.push({
        scheduler: {
            recent_errors: [
                { timestamp: "2026-08-30T15:04:05Z", source_label: "poll", summary: "ok", kind: "network" },
            ],
        },
        authenticated: true,
        mock_mode: false,
    });
    page.listeners.DOMContentLoaded();
    await flush();
    assert.deepEqual(page.requests, ["/api/status"]);
    assert.equal(page.timers.length, 1);
    assert.equal(page.timers[0].delay, 10000);
    assert.equal(page.elements.get("cfn-badge").textContent, "CFN ON");
    assert.match(list.textContent, /poll/);

    page.responses.push({ scheduler: {}, authenticated: false, mock_mode: true });
    page.timers[0].callback();
    await flush();
    assert.deepEqual(page.requests, ["/api/status", "/api/status"]);
    assert.equal(page.timers.length, 1, "history refresh must not create another timer");

    // Pages without the optional history container still update status badges.
    const noHistory = createPage(["cfn-badge", "mock-badge"]);
    noHistory.responses.push({ scheduler: {}, authenticated: true, mock_mode: true });
    noHistory.listeners.DOMContentLoaded();
    await flush();
    assert.equal(noHistory.elements.get("cfn-badge").textContent, "CFN ON");
    assert.equal(noHistory.elements.get("mock-badge").style.display, "inline");
    assert.deepEqual(noHistory.requests, ["/api/status"]);
    assert.equal(noHistory.timers.length, 1);
}

main().catch((error) => {
    console.error(error.stack || error);
    process.exitCode = 1;
});
