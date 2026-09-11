import './pdfjs/compat.mjs';
import * as pdf from './pdfjs/pdf.min.mjs';

pdf.GlobalWorkerOptions.workerSrc = '/static/pdfjs/pdf.worker.shim.mjs';

const status = document.querySelector('#status');
document.querySelector('#print').onclick = () => window.print();

try {
  const id = new URLSearchParams(location.search).get('id');
  if (!id) throw new Error('편집실에서 “인쇄 화면 열기”를 다시 눌러 주세요.');

  const response = await fetch('/api/print/' + encodeURIComponent(id));
  if (!response.ok) throw new Error('인쇄 자료가 만료되었습니다. 편집실에서 다시 열어 주세요.');
  const bytes = await response.arrayBuffer();

  const link = document.querySelector('#download');
  link.href = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }));
  link.download = '주보_양면인쇄.pdf';

  const doc = await pdf.getDocument({
    data: new Uint8Array(bytes),
    standardFontDataUrl: '/static/pdfjs/standard_fonts/',
    isEvalSupported: false,
    useWasm: false,
  }).promise;

  for (let i = 1; i <= doc.numPages; i += 1) {
    const page = await doc.getPage(i);
    const view = page.getViewport({ scale: 300 / 72 });
    const canvas = document.createElement('canvas');
    canvas.width = Math.ceil(view.width);
    canvas.height = Math.ceil(view.height);
    await page.render({ canvasContext: canvas.getContext('2d'), viewport: view }).promise;
    const sheet = document.createElement('section');
    sheet.className = 'sheet ' + (page.getViewport({ scale: 1 }).width > 1000 ? 'a3' : 'a4');
    sheet.append(canvas);
    document.querySelector('#pages').append(sheet);
  }

  status.textContent = '종이 한 장의 앞면과 뒷면이 준비되었습니다. 프린터에서 양면 · 짧은 변 넘김 · 실제 크기 100%로 인쇄하세요.';
  document.querySelector('#print').disabled = false;
} catch (error) {
  status.textContent = error.message;
}
