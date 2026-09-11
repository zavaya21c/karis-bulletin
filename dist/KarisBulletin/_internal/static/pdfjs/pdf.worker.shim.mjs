/* 작업자(worker) 안에서도 호환 코드가 먼저 실행되도록 감싸는 파일입니다.
   모듈은 import 순서대로 실행되므로 compat.mjs 가 항상 먼저 준비됩니다. */
import './compat.mjs';
import './pdf.worker.min.mjs';
