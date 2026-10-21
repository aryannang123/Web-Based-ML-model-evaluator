const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const appSource = fs.readFileSync(
  path.join(__dirname, "..", "js", "app.js"),
  "utf8"
);

function createForm() {
  const handlers = {};
  return {
    handlers,
    resetCalled: false,
    addEventListener(eventName, handler) {
      handlers[eventName] = [...(handlers[eventName] || []), handler];
    },
    reset() {
      this.resetCalled = true;
    },
    querySelector() {
      return this.submitButton;
    }
  };
}

function createHarness(fetchImplementation, includeLogin = false, includeSession = false) {
  const registrationForm = createForm();
  const elements = {
    "registration-form": registrationForm,
    "reg-username": {value: "  test-user  "},
    "reg-email": {value: "  test@example.com  "},
    "reg-password": {value: "StrongPass123!"},
    "registration-feedback": {textContent: "", className: ""}
  };
  let loginForm;

  if (includeLogin) {
    loginForm = createForm();
    loginForm.submitButton = {disabled: false};
    elements["login-form"] = loginForm;
    elements["login-username"] = {value: " test-user "};
    elements["login-password"] = {value: "StrongPass123!"};
    elements["login-feedback"] = {textContent: "", className: ""};
  }
  if (includeSession) elements["current-user"] = {textContent: ""};

  let readyHandler;
  const document = {
    addEventListener(eventName, handler) {
      if (eventName === "DOMContentLoaded") readyHandler = handler;
    },
    getElementById(id) {
      return elements[id] || null;
    }
  };
  const locationCalls = [];
  vm.runInNewContext(appSource, {
    document,
    fetch: fetchImplementation,
    console: {log() {}, error() {}},
    window: {
      location: {
        assign(url) { locationCalls.push(["assign", url]); },
        replace(url) { locationCalls.push(["replace", url]); }
      }
    }
  });

  readyHandler();

  return {
    elements,
    registrationForm,
    loginForm,
    locationCalls,
    async submit(form, eventName = "submit") {
      let defaultPrevented = false;
      const [handler] = form.handlers[eventName] || [];
      assert.equal(typeof handler, "function", `${eventName} listener is initialized`);
      await handler({
        preventDefault() { defaultPrevented = true; },
        currentTarget: form,
        target: form
      });
      return defaultPrevented;
    }
  };
}

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {get: () => "application/json; charset=utf-8"},
    json: async () => body
  };
}

function healthResponse() {
  return jsonResponse(200, {status: "healthy"});
}

test("successful registration displays confirmation and resets the form", async () => {
  let request;
  const harness = createHarness(async (url, options) => {
    if (url === "/api/health") return healthResponse();
    request = {url, options, body: JSON.parse(options.body)};
    return jsonResponse(201, {message: "Registration successful", user_id: 42});
  });

  assert.equal(await harness.submit(harness.registrationForm), true);
  assert.equal(request.url, "/api/auth/register");
  assert.equal(request.options.credentials, "same-origin");
  assert.deepEqual(request.body, {
    username: "test-user",
    email: "test@example.com",
    password: "StrongPass123!"
  });
  assert.equal(harness.elements["registration-feedback"].textContent, "Registration successful");
  assert.match(harness.elements["registration-feedback"].className, /alert-success/);
  assert.equal(harness.registrationForm.resetCalled, true);
  assert.equal(harness.registrationForm.handlers.submit.length, 1);
});

test("duplicate email validation is displayed from the backend", async () => {
  const harness = createHarness(async (url) => url === "/api/health"
    ? healthResponse()
    : jsonResponse(409, {error: "Email already registered"}));

  await harness.submit(harness.registrationForm);
  assert.equal(harness.elements["registration-feedback"].textContent, "Email already registered");
  assert.match(harness.elements["registration-feedback"].className, /alert-danger/);
  assert.equal(harness.registrationForm.resetCalled, false);
});

test("duplicate username validation is displayed from the backend", async () => {
  const harness = createHarness(async (url) => url === "/api/health"
    ? healthResponse()
    : jsonResponse(409, {message: "Username already exists"}));

  await harness.submit(harness.registrationForm);
  assert.equal(harness.elements["registration-feedback"].textContent, "Username already exists");
  assert.match(harness.elements["registration-feedback"].className, /alert-danger/);
});

test("network failures have a distinct message", async () => {
  const harness = createHarness(async (url) => {
    if (url === "/api/health") return healthResponse();
    throw new TypeError("Failed to fetch");
  });

  await harness.submit(harness.registrationForm);
  assert.match(harness.elements["registration-feedback"].textContent, /Unable to reach the server/);
  assert.match(harness.elements["registration-feedback"].className, /alert-danger/);
});

test("non-JSON HTTP responses include their status", async () => {
  const harness = createHarness(async (url) => url === "/api/health"
    ? healthResponse()
    : {
      ok: false,
      status: 502,
      headers: {get: () => "text/html"},
      json: async () => assert.fail("JSON parser should not run for HTML")
    });

  await harness.submit(harness.registrationForm);
  assert.match(harness.elements["registration-feedback"].textContent, /non-JSON response \(HTTP 502\)/);
});

test("malformed JSON HTTP responses include their status", async () => {
  const harness = createHarness(async (url) => url === "/api/health"
    ? healthResponse()
    : {
      ok: false,
      status: 500,
      headers: {get: () => "application/json"},
      json: async () => { throw new SyntaxError("Unexpected token"); }
    });

  await harness.submit(harness.registrationForm);
  assert.match(harness.elements["registration-feedback"].textContent, /invalid JSON \(HTTP 500\)/);
});

test("login listener keeps its API call, same-origin session, and redirect behavior", async () => {
  let loginRequest;
  const harness = createHarness(async (url, options) => {
    if (url === "/api/health") return healthResponse();
    loginRequest = {url, options, body: JSON.parse(options.body)};
    return jsonResponse(200, {redirect_url: "/dashboard"});
  }, true);

  assert.equal(harness.loginForm.handlers.submit.length, 1);
  assert.equal(await harness.submit(harness.loginForm), true);
  assert.equal(loginRequest.url, "/api/auth/login");
  assert.equal(loginRequest.options.credentials, "same-origin");
  assert.deepEqual(loginRequest.body, {
    username: "test-user",
    password: "StrongPass123!"
  });
  assert.deepEqual(harness.locationCalls, [["assign", "/dashboard"]]);
  assert.equal(harness.elements["login-feedback"].textContent, "Signing in...");
  assert.equal(harness.loginForm.submitButton.disabled, false);
});

test("session restoration displays the authenticated user and redirects anonymous sessions", async () => {
  const requests = [];
  const harness = createHarness(async (url, options) => {
    requests.push({url, options});
    if (url === "/api/health") return healthResponse();
    if (url === "/api/auth/session") {
      return jsonResponse(200, {authenticated: true, user: {username: "test-user"}});
    }
    return jsonResponse(200, {authenticated: false});
  }, false, true);

  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(harness.elements["current-user"].textContent, "test-user");
  assert.equal(requests.find((request) => request.url === "/api/auth/session").options.credentials, "same-origin");
  assert.deepEqual(harness.locationCalls, []);

  const anonymous = createHarness(async (url) => url === "/api/health"
    ? healthResponse()
    : jsonResponse(200, {authenticated: false}), false, true);
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(anonymous.locationCalls, [["replace", "/login"]]);
});
