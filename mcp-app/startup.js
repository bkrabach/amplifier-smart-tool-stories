// Retry only the initial read, on a host signal. Mutations and initialized
// editors never enter this path; successful startup remains memoized.
export function createStartupRead(read) {
  let pending, wake, recoveryVersion = 0;
  return {
    recover() {
      recoveryVersion++;
      wake?.();
    },
    start(reportFailure = () => {}) {
      pending ||= (async () => {
        while (true) {
          const observed = recoveryVersion;
          let value;
          try {
            value = await read();
          } catch (error) {
            reportFailure(error);
            await new Promise(resolve => {
              // A recovery signal can arrive before an old failed read settles.
              if (recoveryVersion !== observed) resolve();
              else wake = resolve;
            });
            wake = null;
            continue;
          }
          reportFailure(null);
          return value;
        }
      })();
      return pending;
    },
  };
}
