import assert from "node:assert/strict";
import {test} from "node:test";
import {createStartupRead} from "./startup.js";

const settled = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}

test("successful startup is shared and later notifications do not repeat it", async () => {
  let reads = 0;
  const value = {story: {id: "kept"}}, reports = [];
  const startup = createStartupRead(async () => { reads++; return value; });
  const first = startup.start(error => reports.push(error));
  assert.equal(startup.start(), first);
  assert.equal(await first, value);
  startup.recover(); startup.recover();
  assert.equal(await startup.start(), value);
  assert.equal(reads, 1);
  assert.deepEqual(reports, [null]);
});

test("failed startup waits for recovery and coalesces duplicate notifications", async () => {
  let reads = 0;
  const retry = deferred(), reports = [], failure = Error("Offline");
  const startup = createStartupRead(async () => {
    if (++reads === 1) throw failure;
    return retry.promise;
  });
  const first = startup.start(error => reports.push(error));
  await settled(); await settled();
  assert.equal(reads, 1);
  assert.deepEqual(reports, [failure]);
  startup.recover(); startup.recover(); startup.recover();
  await settled();
  assert.equal(reads, 2);
  startup.recover(); startup.recover();
  assert.equal(startup.start(), first);
  retry.resolve("ready");
  assert.equal(await first, "ready");
  assert.equal(reads, 2);
  assert.deepEqual(reports, [failure, null]);
});

test("a recovery signal racing a failed response is not lost", async () => {
  const initial = deferred();
  let reads = 0;
  const startup = createStartupRead(() => ++reads === 1 ? initial.promise : "ready");
  const pending = startup.start();
  startup.recover(); startup.recover();
  initial.reject(Error("Old disconnected response"));
  assert.equal(await pending, "ready");
  assert.equal(reads, 2);
});

test("another failed read needs another signal instead of a retry loop", async () => {
  let reads = 0;
  const startup = createStartupRead(async () => {
    if (++reads <= 2) throw Error("Still unavailable");
    return "ready";
  });
  const pending = startup.start();
  await settled();
  startup.recover();
  await settled(); await settled();
  assert.equal(reads, 2);
  startup.recover();
  assert.equal(await pending, "ready");
  assert.equal(reads, 3);
});
