/* 오래된 브라우저에서도 미리보기가 동작하도록 최신 표준 기능을 채워 넣습니다.
   번들된 pdf.js는 Map.prototype.getOrInsertComputed 와 Promise.withResolvers 를
   사용하는데, 교회에서 흔히 쓰는 조금 지난 버전의 크롬·엣지·사파리에는 아직
   없습니다. 이 파일을 pdf.js보다 먼저 불러오면 그대로 사용할 수 있습니다.
   원본 pdf.js 파일은 손대지 않습니다. */

for (const target of [Map, WeakMap]) {
  const proto = target && target.prototype;
  if (!proto) continue;
  if (typeof proto.getOrInsertComputed !== 'function') {
    Object.defineProperty(proto, 'getOrInsertComputed', {
      configurable: true, writable: true,
      value(key, callback) {
        if (this.has(key)) return this.get(key);
        const value = callback(key);
        this.set(key, value);
        return value;
      },
    });
  }
  if (typeof proto.getOrInsert !== 'function') {
    Object.defineProperty(proto, 'getOrInsert', {
      configurable: true, writable: true,
      value(key, fallback) {
        if (this.has(key)) return this.get(key);
        this.set(key, fallback);
        return fallback;
      },
    });
  }
}

if (typeof Promise.withResolvers !== 'function') {
  Object.defineProperty(Promise, 'withResolvers', {
    configurable: true, writable: true,
    value() {
      let resolve;
      let reject;
      const promise = new this((ok, fail) => { resolve = ok; reject = fail; });
      return { promise, resolve, reject };
    },
  });
}

if (typeof Array.prototype.findLast !== 'function') {
  Object.defineProperty(Array.prototype, 'findLast', {
    configurable: true, writable: true,
    value(predicate, thisArg) {
      for (let i = this.length - 1; i >= 0; i -= 1) {
        if (predicate.call(thisArg, this[i], i, this)) return this[i];
      }
      return undefined;
    },
  });
}

if (typeof Object.groupBy !== 'function') {
  Object.defineProperty(Object, 'groupBy', {
    configurable: true, writable: true,
    value(items, key) {
      const out = Object.create(null);
      let index = 0;
      for (const item of items) {
        const bucket = key(item, index);
        index += 1;
        (out[bucket] ||= []).push(item);
      }
      return out;
    },
  });
}
