const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const appSource = fs.readFileSync(
  path.join(__dirname, "..", "js", "app.js"),
  "utf8"
);

function createHarness(fetchImplementation) {
  let submitHandler;
  const form = {
    resetCalled: false,
    addEventListener(eventName, handler) {
      if (eventName === "submit") submitHandler = handler;
    },
    reset() {
      this.resetCalled = true;
    }
  };
  const elements = {
    "registration-form": form,
    "reg-username": {value: "  test-user  "},
    "reg-email": {value: "  test@example.com  "},
    "reg-password": {value: "StrongPass123!"},
    "registration-feedback": {textContent: "", className: ""}
  };
  const document = {
    addEventListener() {},
    getElementById(id) {
      return elements[id] || null;
    }
  };

  vm.runInNewContext(appSource, {document, fetch: fetchImplementation, console});

  return {
    elements,
    form,
    async submit() {
      let defaultPrevented = false;
      await submitHandler({
        preventDefault() {
          defaultPrevented = true;
        },
        currentTarget: form
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

test("successful registration displays confirmation and resets the form", async () => {
  let request;
  const harness = createHarness(async (url, options) => {
    request = {url, options, body: JSON.parse(options.body)};
    return jsonResponse(201, {message: "Registration successful", user_id: 42});
  });

  assert.equal(await harness.submit(), true);
  assert.equal(request.url, "/api/auth/register");
  assert.deepEqual(request.body, {
    username: "test-user",
    email: "test@example.com",
    password: "StrongPass123!"
  });
  assert.equal(harness.elements["registration-feedback"].textContent, "Registration successful");
  assert.match(harness.elements["registration-feedback"].className, /alert-success/);
  assert.equal(harness.form.resetCalled, true);
});

test("duplicate email validation is displayed from the backend", async () => {
  const harness = createHarness(async () =>
    jsonResponse(409, {error: "Email already registered"})
  );

  await harness.submit();
  assert.equal(harness.elements["registration-feedback"].textContent, "Email already registered");
  assert.match(harness.elements["registration-feedback"].className, /alert-danger/);
  assert.equal(harness.form.resetCalled, false);
});

test("duplicate username validation is displayed from the backend", async () => {
  const harness = createHarness(async () =>
    jsonResponse(409, {error: "Username already exists"})
  );

  await harness.submit();
  assert.equal(harness.elements["registration-feedback"].textContent, "Username already exists");
  assert.match(harness.elements["registration-feedback"].className, /alert-danger/);
});

test("network failures have a distinct message", async () => {
  const harness = createHarness(async () => {
    throw new TypeError("Failed to fetch");
  });

  await harness.submit();
  assert.match(harness.elements["registration-feedback"].textContent, /Unable to reach the server/);
  assert.match(harness.elements["registration-feedback"].className, /alert-danger/);
});

test("non-JSON HTTP responses include their status", async () => {
  const harness = createHarness(async () => ({
    ok: false,
    status: 502,
    headers: {get: () => "text/html"},
    json: async () => assert.fail("JSON parser should not run for HTML")
  }));

  await harness.submit();
  assert.match(harness.elements["registration-feedback"].textContent, /non-JSON response \(HTTP 502\)/);
});

test("malformed JSON HTTP responses include their status", async () => {
  const harness = createHarness(async () => ({
    ok: false,
    status: 500,
    headers: {get: () => "application/json"},
    json: async () => { throw new SyntaxError("Unexpected token"); }
  }));

  await harness.submit();
  assert.match(harness.elements["registration-feedback"].textContent, /invalid JSON \(HTTP 500\)/);
});
