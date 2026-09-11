'use strict';

/* ------------------------------------------------------------------ *
 * 카리스 주보제작 · 편집 화면
 * 모든 저장과 렌더링은 이 컴퓨터 안의 로컬 서버에서만 이루어집니다.
 * ------------------------------------------------------------------ */

const $ = (selector) => document.querySelector(selector);
const create = (tag, className) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
};

const SECTIONS = {
  basic: {
    title: '기본 정보',
    hint: '주보 표지에 들어가는 내용입니다. 날짜와 말씀 제목만 채워도 한 부가 완성됩니다.',
    fields: [
      ['date', '발행 날짜', 'date'],
      ['issue', '주보 호수', 'text', '예: 1 · 2026-37 · 통권 512'],
      ['sermon', '말씀 제목'],
      ['scripture', '성경 본문', 'text', '예: 요한복음 13:34-35'],
      ['tagline', '표지 문구', 'textarea', '두 줄 정도가 가장 보기 좋습니다.', 'tagline'],
    ],
  },
  worship: {
    title: '예배 순서',
    hint: '순서 서식을 불러온 뒤 담당자만 바꾸면 됩니다. 말씀 순서에는 오늘의 설교 제목이 자동으로 붙습니다.',
    fields: [
      ['service_time', '예배 시간 · 장소', 'text', '예: 주일 오전 11시 · 본당 2층'],
      ['service_note', '예배 안내', 'textarea', null, 'service_note'],
    ],
    extra: 'order',
  },
  article: {
    title: '말씀 · 묵상',
    hint: '글이 짧으면 글자 크기와 줄 간격이 자동으로 넓어지고, 남는 자리에는 말씀 노트 줄이 들어갑니다.',
    fields: [
      ['article_heading', '면 제목', 'text', '예: 마음에 새기는 글'],
      ['article_title', '글 제목'],
      ['article_subtitle', '보조 제목'],
      ['article_quote', '강조 문구', 'textarea', '한 문장으로 적으면 인용구처럼 표시됩니다.'],
      ['article_body', '본문', 'tall', '빈 줄로 문단을 나눕니다. 3단 주보는 두 면에 걸쳐 이어집니다.'],
    ],
  },
  news: {
    title: '소식 · 기도',
    hint: '소식은 한 줄에 하나씩 적으세요. 기도제목은 지면 아래쪽 상자에 들어갑니다.',
    fields: [
      ['announcements', '교회소식', 'tall', '한 줄에 하나씩 입력하세요.', 'announcements'],
      ['prayers', '함께 기도해요', 'textarea', null, 'prayers'],
    ],
  },
  design: {
    title: '디자인 · 용지',
    hint: '아래 표지들은 지금 입력한 내용으로 실제로 만들어 본 모습입니다. 마음에 드는 것을 고르세요.',
    fields: [],
    extra: 'design',
  },
  church: {
    title: '교회 기본 설정',
    hint: '한 번 입력해 두면 매주 그대로 사용합니다. 아래 “교회 기본 설정으로 저장”을 눌러 두세요.',
    fields: [
      ['church', '교회 이름'],
      ['denomination', '교단명'],
      ['established', '교회 설립일', 'text', '예: 1998년 4월 5일'],
      ['address', '교회 주소'],
      ['email', '이메일'],
      ['website', '홈페이지 주소'],
      ['service_time', '기본 예배 시간 · 장소'],
    ],
    extra: 'church',
  },
};

const FORMAT_OPTIONS = [
  ['a4-half', 'A4 반접지 · 4면'],
  ['a4-third', 'A4 3단 양면 · 6면'],
  ['a3-third', 'A3 3단 양면 · 6면'],
];
const FOLD_OPTIONS = [
  ['roll', '안으로 말아 접기 · 접힘면 2mm 좁게'],
  ['accordion', '지그재그 접기 · 동일 폭'],
];

const STORAGE_KEY = 'bulletin-studio-community-draft-v2';

let data = {};
let profile = {};
let presets = { order: [], tagline: [], service_note: [], prayers: [], announcements: [] };
let catalogue = { items: [], groups: [], body_fonts: [], head_fonts: [] };
let section = 'basic';
let previewTimer;
let draftTimer;
let inspectTimer;
let requestVersion = 0;
let pdfDocument;
let saveQueue = Promise.resolve();
let thumbSignature = '';
let thumbBusy = false;
let wantedPage = null;
let filmToken = 0;

const pdfjsReady = import('/static/pdfjs/compat.mjs')
  .then(() => import('/static/pdfjs/pdf.min.mjs'))
  .then((pdf) => {
    pdf.GlobalWorkerOptions.workerSrc = '/static/pdfjs/pdf.worker.shim.mjs';
    return pdf;
  });

/* ---------------------------- helpers ---------------------------- */

function toast(message) {
  const box = $('#toast');
  box.textContent = message;
  box.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { box.hidden = true; }, 7000);
}

async function request(path, payload) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let message = '작업을 완료하지 못했습니다.';
    try { message = (await response.json()).error || message; } catch { /* keep default */ }
    throw new Error(message);
  }
  return response;
}

function action(id, handler) {
  $(id).onclick = async () => {
    const button = $(id);
    button.disabled = true;
    try { await handler(); } catch (error) { toast(error.message); } finally { button.disabled = false; }
  };
}

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const link = create('a');
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

function reportSaved(result) {
  $('#save-result').textContent = '저장 완료: ' + result.path;
  toast('파일을 저장했습니다. 아래 “저장 폴더 열기”로 확인하세요.');
}

/* ---------------------------- state ------------------------------ */

function saveDraft() {
  const snapshot = JSON.parse(JSON.stringify(data));
  saveQueue = saveQueue
    .catch(() => {})
    .then(() => request('/api/draft', { data: snapshot }))
    .then(() => { $('#autosave').textContent = '이 컴퓨터에 자동 저장됨 · ' + new Date().toLocaleTimeString('ko-KR'); })
    .catch(() => { $('#autosave').textContent = '서버 자동 저장 실패 · 브라우저 초안은 유지됩니다.'; });
  return saveQueue;
}

function changed() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    localStorage.setItem(STORAGE_KEY + '-updated', String(Date.now()));
  } catch {
    toast('브라우저 저장 공간이 부족합니다. 편집 파일을 저장해 주세요.');
  }
  updateEdition();
  runLocalChecks();
  clearTimeout(previewTimer);
  previewTimer = setTimeout(preview, 620);
  clearTimeout(draftTimer);
  draftTimer = setTimeout(saveDraft, 800);
  clearTimeout(inspectTimer);
  inspectTimer = setTimeout(runServerChecks, 1400);
  $('#autosave').textContent = '변경 내용을 저장하는 중…';
}

function designName(id) {
  return catalogue.items.find((item) => item.id === id)?.name || '';
}

function updateEdition() {
  $('#edition').textContent = `${data.date} · ${data.issue || ''}호`.replace('· 호', '');
  $('#edition-design').textContent = designName(data.design);
  const formatLabel = FORMAT_OPTIONS.find((option) => option[0] === data.format)?.[1] || '';
  $('#format-chip').textContent = formatLabel;
  const trifold = data.format !== 'a4-half';
  $('#fold-guide').textContent = trifold
    ? `${data.format === 'a3-third' ? 'A3' : 'A4'} 가로 · 양면 · 짧은 변 넘김 · 실제 크기 100%. 앞면 5 | 6 | 1, 뒷면 2 | 3 | 4. `
      + (data.fold === 'roll'
        ? '5면을 안으로 먼저 접고 1면 표지가 겉으로 오게 덮습니다. 접히는 면은 2mm 좁습니다.'
        : '같은 폭의 세 면을 지그재그로 접습니다.')
      + ' 처음 쓰실 때는 시험 출력으로 접는 방향을 한 번 확인하세요.'
    : 'A4 가로 · 양면 · 짧은 변 넘김 · 실제 크기 100%. 앞면 4 | 1, 뒷면 2 | 3.';
}

let localNotes = [];
let serverNotes = [];

function showChecks() {
  const all = [...localNotes, ...serverNotes];
  const box = $('#checks');
  box.replaceChildren();
  if (!all.length) { box.hidden = true; return; }
  const list = create('ul');
  for (const note of all) {
    const item = create('li');
    item.textContent = note;
    list.append(item);
  }
  box.append(list);
  box.hidden = false;
}

function runLocalChecks() {
  const notes = [];
  if (data.date && new Date(data.date + 'T12:00:00').getDay() !== 0) {
    notes.push('발행 날짜가 일요일이 아닙니다. 의도한 날짜인지 확인해 주세요.');
  }
  if (data.announcements && /지난주|지난 주/.test(data.announcements)) {
    notes.push('교회소식의 “지난주” 표현이 이번 주에도 맞는지 확인해 주세요.');
  }
  if (!data.tagline.trim()) notes.push('표지 문구가 비어 있습니다. 기본 정보에서 한 줄 넣어 보세요.');
  localNotes = notes;
  showChecks();
}

async function runServerChecks() {
  try {
    const result = await (await request('/api/inspect', { data })).json();
    serverNotes = result.notes || [];
  } catch {
    serverNotes = [];
  }
  showChecks();
}

/* ---------------------------- fields ----------------------------- */

function exampleBox(key, label) {
  const list = presets[key];
  if (!list || !list.length) return null;
  const box = create('details', 'examples');
  const summary = create('summary');
  summary.textContent = label || '예문 넣기';
  box.append(summary);
  const chips = create('div', 'chips');
  for (const text of list) {
    const button = create('button');
    button.type = 'button';
    button.textContent = text.replace(/\n/g, ' / ');
    button.onclick = () => {
      const current = (data[key] || '').trim();
      if (key === 'announcements' || key === 'prayers') {
        data[key] = current ? current + '\n' + text : text;
      } else {
        data[key] = text;
      }
      changed();
      buildFields();
    };
    chips.append(button);
  }
  box.append(chips);
  return box;
}

function textField(key, title, type, hint, presetKey) {
  const label = create('label');
  label.textContent = title;
  const tall = type === 'tall';
  const input = create(type === 'textarea' || tall ? 'textarea' : 'input');
  if (input.tagName === 'INPUT') input.type = type === 'text' || !type ? 'text' : type;
  if (tall) input.className = 'tall';
  input.name = key;
  input.value = data[key] || '';
  input.spellcheck = true;
  input.maxLength = tall || type === 'textarea' ? 8000 : 120;
  input.oninput = () => { data[key] = input.value; changed(); };
  label.append(input);
  if (hint) {
    const small = create('small');
    small.textContent = hint;
    label.append(small);
  }
  const wrapper = create('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'column';
  wrapper.style.gap = '7px';
  wrapper.append(label);
  const examples = presetKey ? exampleBox(presetKey) : null;
  if (examples) wrapper.append(examples);
  return wrapper;
}

function selectField(key, title, options, hint, onChange) {
  const label = create('label');
  label.textContent = title;
  const select = create('select');
  for (const [value, name] of options) select.append(new Option(name, value));
  select.value = data[key] || options[0][0];
  select.onchange = () => {
    data[key] = select.value;
    changed();
    if (onChange) onChange();
  };
  label.append(select);
  if (hint) {
    const small = create('small');
    small.textContent = hint;
    label.append(small);
  }
  return label;
}

function checkField(key, title, trueValue, falseValue) {
  const label = create('label', 'checkbox');
  const input = create('input');
  input.type = 'checkbox';
  input.checked = trueValue === undefined ? Boolean(data[key]) : data[key] === trueValue;
  input.onchange = () => {
    data[key] = trueValue === undefined ? input.checked : (input.checked ? trueValue : falseValue);
    changed();
  };
  label.append(input, document.createTextNode(title));
  return label;
}

function buildFields() {
  const config = SECTIONS[section];
  $('#section-title').textContent = config.title;
  $('#section-hint').textContent = config.hint || '';
  $('#section-number').textContent =
    String(Object.keys(SECTIONS).indexOf(section) + 1).padStart(2, '0') + ' / CONTENT';

  const root = $('#fields');
  root.replaceChildren();
  for (const [key, title, type, hint, presetKey] of config.fields) {
    root.append(textField(key, title, type || 'text', hint, presetKey));
  }
  if (config.extra === 'order') root.append(orderBox());
  if (config.extra === 'design') root.append(designPanel());
  if (config.extra === 'church') root.append(churchPanel());
}

/* ------------------------ worship order -------------------------- */

function orderBox() {
  const box = create('section', 'order-box');
  const heading = create('h3');
  heading.textContent = '예배 순서 · 순서와 담당을 따로 입력합니다';
  box.append(heading);

  const help = create('p', 'help');
  help.textContent = '서식을 불러온 다음 담당자만 고치면 됩니다. 위·아래 버튼으로 순서를 바꿀 수 있습니다.';
  box.append(help);

  if (presets.order.length) {
    const label = create('label');
    label.textContent = '예배 순서 서식 불러오기';
    const select = create('select');
    select.append(new Option('서식을 선택하세요', ''));
    for (const preset of presets.order) select.append(new Option(preset.name, preset.name));
    select.onchange = () => {
      const preset = presets.order.find((item) => item.name === select.value);
      select.value = '';
      if (!preset) return;
      if (!confirm(`“${preset.name}” 서식으로 지금 순서를 바꿀까요? 현재 입력한 순서는 사라집니다.`)) return;
      data.order = preset.rows.join('\n');
      changed();
      buildFields();
      toast('서식을 불러왔습니다. 담당자를 확인해 주세요.');
    };
    label.append(select);
    box.append(label);
  }

  let rows = (data.order || '').split('\n').filter((line) => line.trim()).map((line) => {
    const parts = line.includes('|') ? line.split(/\|(.*)/s) : line.split(/\s+(.*)/s);
    return [(parts[0] || '').trim(), (parts[1] || '').trim()];
  });

  const sync = () => { data.order = rows.map((row) => row.join(' | ')).join('\n'); changed(); };

  const paint = () => {
    box.querySelectorAll('.order-row,.add-row').forEach((node) => node.remove());
    rows.forEach((row, index) => {
      const line = create('div', 'order-row');
      row.forEach((value, column) => {
        const input = create('input');
        input.type = 'text';
        input.value = value;
        input.placeholder = column ? '담당자 또는 내용' : '예: 찬양';
        input.setAttribute('aria-label', `${index + 1}번째 ${column ? '담당자 또는 내용' : '예배 순서'}`);
        input.maxLength = 300;
        input.oninput = () => { rows[index][column] = input.value; sync(); };
        line.append(input);
      });
      const actions = create('div', 'row-actions');
      const moves = [
        ['↑', () => { [rows[index - 1], rows[index]] = [rows[index], rows[index - 1]]; }, index === 0],
        ['↓', () => { [rows[index + 1], rows[index]] = [rows[index], rows[index + 1]]; }, index === rows.length - 1],
        ['삭제', () => { rows.splice(index, 1); }, false],
      ];
      for (const [text, run, disabled] of moves) {
        const button = create('button');
        button.type = 'button';
        button.textContent = text;
        button.disabled = disabled;
        button.onclick = () => { run(); sync(); paint(); };
        actions.append(button);
      }
      line.append(actions);
      box.append(line);
    });
    const add = create('button', 'add-row');
    add.type = 'button';
    add.textContent = '＋ 순서 추가';
    add.onclick = () => { rows.push(['', '']); paint(); };
    box.append(add);
  };

  paint();
  return box;
}

/* ------------------------ design gallery ------------------------- */

function thumbKey() {
  return JSON.stringify([
    data.church, data.denomination, data.date, data.issue, data.tagline, data.sermon,
    data.scripture, data.service_time, data.address, data.email, data.format, data.fold,
    data.head_font, data.body_font, data.logo ? data.logo.length : 0,
    data.custom_background ? data.custom_background.length : 0,
    data.custom_top, data.custom_color, data.custom_panel, data.custom_show_text, data.custom_fit,
  ]);
}

async function loadThumbnails(force) {
  const grid = $('#design-grid');
  if (!grid) return;
  const key = thumbKey();
  if (!force && key === thumbSignature) return;
  if (thumbBusy) return;
  thumbBusy = true;
  const status = $('#design-status');
  if (status) status.textContent = '표지를 만드는 중…';
  try {
    const response = await request('/api/design-previews', { data });
    const bytes = new Uint8Array(await response.arrayBuffer());
    const pdf = await pdfjsReady;
    const doc = await pdf.getDocument({
      data: bytes,
      standardFontDataUrl: '/static/pdfjs/standard_fonts/',
      isEvalSupported: false,
      useWasm: false,
    }).promise;
    for (let index = 0; index < catalogue.items.length && index < doc.numPages; index += 1) {
      const holder = grid.querySelector(`[data-thumb="${catalogue.items[index].id}"]`);
      if (!holder) continue;
      const page = await doc.getPage(index + 1);
      const viewport = page.getViewport({ scale: 0.62 });
      const canvas = create('canvas');
      canvas.width = Math.ceil(viewport.width);
      canvas.height = Math.ceil(viewport.height);
      await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
      holder.replaceChildren(canvas);
    }
    doc.destroy();
    thumbSignature = key;
    if (status) status.textContent = '지금 입력한 내용으로 만든 표지입니다.';
  } catch (error) {
    if (status) status.textContent = '표지 미리보기를 만들지 못했습니다: ' + error.message;
  } finally {
    thumbBusy = false;
  }
}

function designPanel() {
  const wrapper = create('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'column';
  wrapper.style.gap = '16px';

  const row = create('div', 'field-row');
  row.append(
    selectField('format', '용지와 면 구성', FORMAT_OPTIONS, null, () => { thumbSignature = ''; buildFields(); }),
    selectField('fold', '3단 접는 방식', FOLD_OPTIONS, data.format === 'a4-half' ? '반접지에서는 사용하지 않습니다.' : null),
  );
  if (data.format === 'a4-half') row.querySelectorAll('select')[1].disabled = true;
  wrapper.append(row);

  const tools = create('div', 'design-tools');
  const status = create('p', 'help');
  status.id = 'design-status';
  status.style.flex = '1';
  status.textContent = '표지를 만드는 중…';
  const refresh = create('button');
  refresh.type = 'button';
  refresh.textContent = '표지 미리보기 새로 만들기';
  refresh.onclick = () => loadThumbnails(true);
  tools.append(status, refresh);
  wrapper.append(tools);

  const grid = create('div');
  grid.id = 'design-grid';
  for (const group of catalogue.groups) {
    const members = catalogue.items.filter((item) => item.group === group);
    if (!members.length) continue;
    const title = create('p', 'design-group');
    title.textContent = group;
    grid.append(title);
    const cells = create('div', 'design-grid');
    for (const item of members) {
      const card = create('button', 'design-card');
      card.type = 'button';
      card.setAttribute('aria-pressed', String(data.design === item.id));
      const thumb = create('span', 'thumb');
      thumb.dataset.thumb = item.id;
      thumb.style.background = item.paper;
      const meta = create('span', 'meta');
      const name = create('b');
      name.textContent = item.name;
      const blurb = create('small');
      blurb.textContent = item.blurb;
      meta.append(name, blurb);
      card.append(thumb, meta);
      card.onclick = () => {
        data.design = item.id;
        changed();
        buildFields();
        if (item.id === 'custom' && !data.custom_background) {
          toast('아래에서 표지로 쓸 PNG·JPG 이미지를 등록해 주세요.');
        }
      };
      cells.append(card);
    }
    grid.append(cells);
  }
  wrapper.append(grid);

  const fonts = create('div', 'field-row');
  fonts.append(
    selectField('head_font', '제목 글꼴',
      [['', '디자인 기본값'], ...catalogue.head_fonts.map((font) => [font.id, font.name])]),
    selectField('body_font', '본문 글꼴',
      [['', '디자인 기본값'], ...catalogue.body_fonts.map((font) => [font.id, font.name])]),
  );
  wrapper.append(fonts);

  const toggles = create('div');
  toggles.style.display = 'flex';
  toggles.style.flexDirection = 'column';
  toggles.style.gap = '9px';
  toggles.append(
    checkField('sermon_notes', '묵상 면에 남는 자리가 있으면 “말씀 노트” 줄 넣기', 'on', 'off'),
    checkField('public_names', '홈페이지 공개본에서 성도 이름 가리기 (홍길동 집사 → 홍○○ 집사)', 'mask', 'show'),
    checkField('public_prayers', '홈페이지 공개본에 기도제목 포함'),
    checkField('public_contacts', '홈페이지 공개본에 주소 · 이메일 포함'),
  );
  const privacy = create('p', 'help');
  privacy.textContent = '이름 가리기는 홈페이지 공개본에만 적용됩니다. 교회에서 나눠 주는 인쇄용·읽기용 주보는 그대로 나옵니다. 직분(목사·집사·장로·권사·성도·형제·자매 등)이 뒤에 붙은 이름을 찾아 가립니다.';
  toggles.append(privacy);
  wrapper.append(toggles);

  const samples = create('button');
  samples.type = 'button';
  samples.textContent = '전체 디자인 샘플집 PDF 저장';
  samples.onclick = async () => {
    try { reportSaved(await (await request('/api/save-samples', { data })).json()); }
    catch (error) { toast(error.message); }
  };
  wrapper.append(samples);
  wrapper.append(customPanel());

  setTimeout(() => loadThumbnails(false), 40);
  return wrapper;
}

function customPanel() {
  const box = create('section', 'custom-design-box');
  const heading = create('h3');
  heading.textContent = '내 디자인 · 직접 만든 표지 배경';
  box.append(heading);

  const help = create('p', 'help');
  help.textContent = 'PNG·JPG(4MB · 1200만 화소 이하)를 등록하세요. PDF·AI·PSD는 PNG나 JPG로 내보낸 뒤 등록해 주세요.';
  box.append(help);

  const label = create('label');
  label.textContent = '배경 파일 등록';
  const file = create('input');
  file.type = 'file';
  file.accept = 'image/png,image/jpeg';
  label.append(file);
  box.append(label);

  const choose = create('select');
  choose.setAttribute('aria-label', '등록한 내 디자인');
  box.append(choose);

  const reload = async () => {
    const result = await (await fetch('/api/design-library')).json();
    choose.replaceChildren(new Option('등록한 배경을 선택하세요', ''));
    for (const item of result.items) choose.append(new Option(item.name, item.id));
  };
  reload().catch((error) => toast(error.message));

  const apply = (result) => {
    if (result.error) throw new Error(result.error);
    data.custom_background = result.image;
    data.design = 'custom';
    thumbSignature = '';
    changed();
    buildFields();
    toast('내 디자인을 표지에 적용했습니다. 글자 위치를 조절해 주세요.');
  };

  file.onchange = async () => {
    try {
      const chosen = file.files[0];
      if (!chosen) return;
      if (chosen.size > 4000000) throw new Error('4MB 이하 이미지를 선택하세요.');
      const image = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(chosen);
      });
      apply(await (await request('/api/register-design', { name: chosen.name, image })).json());
    } catch (error) {
      toast(error.message);
    } finally {
      file.value = '';
    }
  };

  choose.onchange = async () => {
    if (!choose.value) return;
    try { apply(await (await fetch('/api/design-image/' + encodeURIComponent(choose.value))).json()); }
    catch (error) { toast(error.message); }
  };

  const buttons = create('div', 'file-actions');
  for (const [text, run] of [
    ['디자인 폴더 열기', () => request('/api/open-design-folder', {})],
    ['폴더 목록 새로고침', reload],
  ]) {
    const button = create('button');
    button.type = 'button';
    button.textContent = text;
    button.onclick = () => Promise.resolve(run()).catch((error) => toast(error.message));
    buttons.append(button);
  }
  box.append(buttons);

  if (data.design === 'custom') {
    box.append(selectField('custom_fit', '이미지 맞춤',
      [['contain', '이미지 전체 보이기 · 여백 생길 수 있음'], ['cover', '면 가득 채우기 · 가장자리 잘림']]));
    const top = create('label');
    top.textContent = '글자 시작 위치 · 위에서 mm';
    const number = create('input');
    number.type = 'number';
    number.min = '10';
    number.max = '170';
    number.value = data.custom_top;
    number.oninput = () => { data.custom_top = number.value; changed(); };
    top.append(number);
    box.append(top);
    box.append(selectField('custom_color', '글자 색상', [['dark', '짙은 글씨'], ['light', '흰 글씨']]));
    box.append(checkField('custom_panel', '글자 뒤에 반투명 바탕 깔기'));
    box.append(checkField('custom_show_text', '배경 위에 교회 정보와 주보 내용 표시'));
    const note = create('p', 'help');
    note.textContent = '완성된 표지 이미지라면 내용 표시를 끄세요. 배경에 이미 들어 있는 글자와 개인정보는 공개 설정으로 지워지지 않습니다.';
    box.append(note);
  }
  return box;
}

/* ------------------------- church panel -------------------------- */

function churchPanel() {
  const box = create('div');
  box.style.display = 'flex';
  box.style.flexDirection = 'column';
  box.style.gap = '11px';

  const label = create('label');
  label.textContent = '교회 로고 · PNG (1MB 이하)';
  const input = create('input');
  input.type = 'file';
  input.accept = 'image/png';
  input.onchange = () => {
    const file = input.files[0];
    if (!file) return;
    if (file.size > 1000000) { toast('1MB 이하 PNG를 선택해 주세요.'); return; }
    const reader = new FileReader();
    reader.onload = () => {
      data.logo = reader.result;
      thumbSignature = '';
      changed();
      buildFields();
      toast('로고를 표지에 넣었습니다. 아래에서 크기와 위치를 조절하세요.');
    };
    reader.readAsDataURL(file);
  };
  label.append(input);
  const hint = create('small');
  hint.textContent = '배경이 투명한 PNG를 쓰면 어두운 표지에서도 잘 보입니다.';
  label.append(hint);
  box.append(label);

  if (data.logo) {
    const controls = create('div');
    controls.style.display = 'flex';
    controls.style.flexDirection = 'column';
    controls.style.gap = '11px';

    const size = create('label');
    size.textContent = '로고 크기 · 세로 길이 mm';
    const range = create('div', 'slider-row');
    const slider = create('input');
    slider.type = 'range';
    slider.min = '6';
    slider.max = '90';
    slider.step = '1';
    slider.value = data.logo_size || '22';
    const number = create('input');
    number.type = 'number';
    number.min = '6';
    number.max = '90';
    number.value = data.logo_size || '22';
    const sync = (value) => {
      data.logo_size = String(value);
      slider.value = String(value);
      number.value = String(value);
      thumbSignature = '';
      changed();
    };
    slider.oninput = () => sync(slider.value);
    number.oninput = () => sync(number.value);
    range.append(slider, number);
    size.append(range);
    const sizeHint = create('small');
    sizeHint.textContent = '22mm 정도가 기본입니다. 표지 폭을 넘으면 자동으로 줄어듭니다.';
    size.append(sizeHint);
    controls.append(size);

    controls.append(selectField('logo_place', '로고 위치', [
      ['above', '교회 이름 위 (장식 대신)'],
      ['top', '표지 맨 위'],
      ['bottom', '표지 맨 아래'],
      ['free', '직접 지정'],
    ], '「직접 지정」을 고르면 아래에서 가로·세로를 직접 정할 수 있습니다.', () => {
      thumbSignature = '';
      buildFields();
    }));

    if (data.logo_place === 'free') {
      const spot = create('div', 'field-row');
      const across = create('label');
      across.textContent = '가로 위치 · 왼쪽 0 ~ 오른쪽 100';
      const ax = create('input');
      ax.type = 'number';
      ax.min = '0';
      ax.max = '100';
      ax.value = data.logo_x || '50';
      ax.oninput = () => { data.logo_x = ax.value; thumbSignature = ''; changed(); };
      across.append(ax);
      const down = create('label');
      down.textContent = '세로 위치 · 위에서 mm';
      const ay = create('input');
      ay.type = 'number';
      ay.min = '0';
      ay.max = '400';
      ay.value = data.logo_y || '30';
      ay.oninput = () => { data.logo_y = ay.value; thumbSignature = ''; changed(); };
      down.append(ay);
      spot.append(across, down);
      controls.append(spot);
      const spotHint = create('p', 'help');
      spotHint.textContent = '가로 50이면 가운데입니다. 세로는 종이 위쪽 끝에서부터 잰 길이입니다. 옮기면서 오른쪽 미리보기로 확인하세요.';
      controls.append(spotHint);
    }
    box.append(controls);
  }

  const buttons = create('div', 'file-actions');
  const actions = [
    ['로고 제거', () => { data.logo = ''; thumbSignature = ''; changed(); buildFields(); toast('로고를 지웠습니다.'); }],
    ['교회 기본 설정으로 저장', async () => {
      await request('/api/profile', { data });
      profile = await (await fetch('/api/profile')).json();
      toast('이 교회의 기본 설정을 저장했습니다. 다음 주보에도 그대로 쓰입니다.');
    }],
    ['저장한 교회 설정 적용', () => {
      if (!Object.keys(profile).length) { toast('저장한 교회 설정이 없습니다.'); return; }
      if (!confirm('현재 교회 정보와 디자인에 저장해 둔 기본 설정을 적용할까요?')) return;
      data = { ...data, ...profile };
      thumbSignature = '';
      changed();
      buildFields();
    }],
  ];
  for (const [text, run] of actions) {
    const button = create('button');
    button.type = 'button';
    button.textContent = text;
    button.onclick = async () => { try { await run(); } catch (error) { toast(error.message); } };
    buttons.append(button);
  }
  box.append(buttons);
  return box;
}

/* ---------------------------- preview ---------------------------- */

async function showPage() {
  if (!pdfDocument) return;
  const current = pdfDocument;
  const number = Math.min(Math.max(1, Number($('#preview-page').value || 1)), current.numPages);
  const page = await current.getPage(number);
  const canvas = create('canvas');
  const viewport = page.getViewport({ scale: 1.6 });
  canvas.width = Math.ceil(viewport.width);
  canvas.height = Math.ceil(viewport.height);
  await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
  if (current === pdfDocument) $('#preview').replaceChildren(canvas);
}

function pageLabels(mode, count) {
  if (mode === 'print') {
    return count === 2 ? ['인쇄 앞면', '인쇄 뒷면'] : Array.from({ length: count }, (_, i) => `인쇄 ${i + 1}면`);
  }
  const names = count === 4
    ? ['1면 표지', '2면 예배 순서', '3면 말씀 · 묵상', '4면 소식 · 기도']
    : ['1면 표지', '2면 예배 순서', '3면 말씀 · 묵상', '4면 묵상 이어서', '5면 교회 소식', '6면 교회 안내'];
  return Array.from({ length: count }, (_, i) => names[i] || `${i + 1}면`);
}

/* 왼쪽에서 고른 단계가 주보의 몇 번째 면인지. */
function sectionPage() {
  const trifold = data.format !== 'a4-half';
  const map = {
    basic: 1,
    worship: 2,
    article: 3,
    news: trifold ? 5 : 4,
    design: 1,
    church: trifold ? 6 : 1,
  };
  return map[section] || 1;
}

function markFilm() {
  const current = Number($('#preview-page').value || 1);
  for (const item of $('#filmstrip').querySelectorAll('.film')) {
    item.setAttribute('aria-pressed', String(Number(item.dataset.page) === current));
  }
}

async function buildFilmstrip(doc, labels, wide) {
  const token = ++filmToken;
  const strip = $('#filmstrip');
  strip.replaceChildren();
  for (let i = 1; i <= doc.numPages; i += 1) {
    const item = create('button', 'film' + (wide ? ' wide' : ''));
    item.type = 'button';
    item.dataset.page = String(i);
    const holder = create('span', 'film-thumb');
    const caption = create('small');
    caption.textContent = labels[i - 1] || `${i}면`;
    item.append(holder, caption);
    item.onclick = () => {
      $('#preview-page').value = String(i);
      markFilm();
      showPage().catch((error) => toast(error.message));
    };
    strip.append(item);
  }
  markFilm();
  for (let i = 1; i <= doc.numPages; i += 1) {
    if (token !== filmToken || doc !== pdfDocument) return;
    const page = await doc.getPage(i);
    const viewport = page.getViewport({ scale: wide ? 0.16 : 0.30 });
    const canvas = create('canvas');
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
    if (token !== filmToken) return;
    const holder = strip.querySelector(`.film[data-page="${i}"] .film-thumb`);
    if (holder) holder.replaceChildren(canvas);
  }
}

/* 왼쪽 단계를 바꾸면 오른쪽 미리보기도 그 면으로 옮겨 갑니다. */
async function followSection() {
  if (!$('#follow').checked) return;
  const target = sectionPage();
  if ($('#preview-mode').value !== 'reading') {
    $('#preview-mode').value = 'reading';
    wantedPage = target;
    await preview();
    return;
  }
  if (!pdfDocument) { wantedPage = target; return; }
  $('#preview-page').value = String(Math.min(target, pdfDocument.numPages));
  markFilm();
  await showPage();
}

async function preview() {
  const version = ++requestVersion;
  $('#status').textContent = '지면을 만드는 중…';
  try {
    const mode = $('#preview-mode').value;
    const response = await request('/api/render', { data, mode });
    const pdf = await pdfjsReady;
    const doc = await pdf.getDocument({
      data: new Uint8Array(await response.arrayBuffer()),
      standardFontDataUrl: '/static/pdfjs/standard_fonts/',
      isEvalSupported: false,
      useWasm: false,
    }).promise;
    if (version !== requestVersion) { doc.destroy(); return; }
    const previous = pdfDocument;
    pdfDocument = doc;
    const picker = $('#preview-page');
    const wanted = wantedPage || Number(picker.value || 1);
    wantedPage = null;
    const labels = pageLabels(mode, doc.numPages);
    picker.replaceChildren(...labels.map((label, index) => new Option(label, index + 1)));
    picker.value = String(Math.min(Math.max(1, wanted), doc.numPages));
    await showPage();
    buildFilmstrip(doc, labels, mode === 'print').catch(() => {});
    if (previous) previous.destroy();
    if (version !== requestVersion) return;
    $('#error').hidden = true;
    $('#status').textContent = '미리보기 반영 완료';
  } catch (error) {
    if (version !== requestVersion) return;
    $('#error').textContent = error.message;
    $('#error').hidden = false;
    $('#status').textContent = '수정이 필요합니다 · 아래 미리보기는 최신 내용이 아닙니다.';
  }
}

async function historyList() {
  const result = await (await fetch('/api/history')).json();
  $('#history').replaceChildren(new Option('수정본 선택', ''));
  for (const id of result.items) $('#history').append(new Option(id.replace('bulletin-', ''), id));
}

/* ----------------------------- wiring ---------------------------- */

$('#fields').onsubmit = (event) => event.preventDefault();

$('#navigation').onclick = (event) => {
  const button = event.target.closest('button[data-section]');
  if (!button) return;
  section = button.dataset.section;
  for (const item of $('#navigation').querySelectorAll('button')) {
    item.classList.toggle('active', item === button);
  }
  buildFields();
  followSection().catch((error) => toast(error.message));
};

$('#preview-mode').onchange = preview;
$('#preview-page').onchange = () => {
  markFilm();
  showPage().catch((error) => toast(error.message));
};
$('#follow').onchange = () => {
  if ($('#follow').checked) followSection().catch((error) => toast(error.message));
};
$('#show-preview').onclick = () => $('.preview-area').scrollIntoView({ behavior: 'smooth' });
$('#refresh').onclick = preview;

action('#save', async () => {
  await request('/api/save', { data });
  await historyList();
  toast('수정본을 보관했습니다. 이전 수정본도 그대로 남아 있습니다.');
});

action('#next-week', async () => {
  if (!confirm('현재 내용을 보관하고 다음 주 날짜로 복사할까요? 교회소식과 담당자는 직접 확인해 주세요.')) return;
  await request('/api/save', { data });
  await historyList();
  const next = new Date(data.date + 'T12:00:00');
  next.setDate(next.getDate() + 7);
  data.date = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-${String(next.getDate()).padStart(2, '0')}`;
  data.issue = data.issue.replace(/\d+$/, (n) => String(Number(n) + 1));
  thumbSignature = '';
  changed();
  buildFields();
  toast('다음 주로 복사했습니다. 교회소식의 날짜와 담당자를 확인해 주세요.');
});

for (const [id, kind] of [
  ['#download-print', 'print'], ['#download-reading', 'reading'], ['#download-public', 'public'],
  ['#export-data', 'content'], ['#bundle', 'bundle'],
]) {
  action(id, async () => reportSaved(await (await request('/api/save-document', { data, kind })).json()));
}

action('#open-folder', async () => { await request('/api/open-folder', { data }); });
action('#backup', async () => reportSaved(await (await request('/api/backup', { data })).json()));

action('#restore', async () => {
  const id = $('#history').value;
  if (!id) { toast('복원할 수정본을 선택하세요.'); return; }
  if (!confirm('현재 초안을 선택한 수정본으로 바꿀까요?')) return;
  const incoming = await (await fetch('/api/history/' + encodeURIComponent(id))).json();
  if (incoming.error) throw new Error(incoming.error);
  data = { ...data, ...incoming };
  thumbSignature = '';
  changed();
  buildFields();
  toast('수정본을 복원했습니다.');
});

$('#import-data').onchange = async (event) => {
  try {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 8000000) throw new Error('8MB 이하 편집 파일을 사용해 주세요.');
    const incoming = { ...data, ...JSON.parse(await file.text()) };
    await request('/api/render', { data: incoming });
    if (!confirm('현재 초안에 이 편집 파일을 불러올까요?')) return;
    data = incoming;
    thumbSignature = '';
    changed();
    buildFields();
    toast('편집 파일을 불러왔습니다.');
  } catch (error) {
    toast(error.message);
  } finally {
    event.target.value = '';
  }
};

action('#print', async () => {
  const tab = window.open('about:blank', '_blank');
  if (tab) tab.opener = null;
  try {
    const result = await (await request('/api/print', { data })).json();
    if (tab) tab.location.href = result.url; else location.href = result.url;
  } catch (error) {
    if (tab) tab.close();
    throw error;
  }
});

action('#share-image', async () => {
  if (!$('#error').hidden) throw new Error('미리보기 오류를 먼저 수정해 주세요.');
  const canvas = $('#preview canvas');
  if (!canvas) throw new Error('미리보기를 먼저 만들어 주세요.');
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
  const label = $('#preview-page').selectedOptions[0]?.textContent || '면';
  download(blob, `${data.church}_${data.date}_${label}.png`);
  $('#save-result').textContent = 'PNG 다운로드를 요청했습니다. 브라우저의 다운로드 폴더를 확인하세요.';
});

/* ----------------------------- start ----------------------------- */

async function showColophon() {
  try {
    const about = await (await fetch('/api/about')).json();
    if (about.version) $('#about-version').textContent = about.version.split('.').slice(0, 2).join('.');

    // assets/brand-logo.png 를 넣어 두면 ✝ 자리에 그 로고가 들어갑니다.
    if (about.brand_logo) {
      const box = document.querySelector('.brand .mark');
      if (box) {
        const image = create('img');
        image.src = '/assets/brand-logo.png';
        image.alt = about.project || '';
        image.onload = () => { box.classList.add('has-logo'); box.replaceChildren(image); };
      }
    }
    const owner = [about.year, about.author].filter(Boolean).join(' ');
    $('#about-copy').textContent = owner ? `© ${owner}` : '';
    $('#about-notice').textContent = about.notice || '';

    // 후원 안내는 계좌나 링크가 채워져 있을 때만 보여 줍니다.
    const account = (about.support_account || '').trim();
    const link = (about.support_link || '').trim();
    if (account || link) {
      $('#support-notice').textContent = about.support_notice || '';
      $('#support-account').textContent = account;
      $('#support-account').hidden = !account;
      const anchor = $('#support-link');
      if (link && /^https?:\/\//i.test(link)) {
        anchor.href = link;
        anchor.hidden = false;
      }
      $('#support').hidden = false;
    }
  } catch { /* 표시만 생략합니다 */ }
}

(async () => {
  showColophon();
  try {
    data = await (await fetch('/api/current')).json();
    profile = await (await fetch('/api/profile')).json();
    catalogue = await (await fetch('/api/designs')).json();
    try { presets = await (await fetch('/api/presets')).json().then((r) => r.items || r); } catch { /* optional */ }
    const draft = await (await fetch('/api/draft')).json();
    data = { ...data, ...draft.data };
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const stamp = Number(localStorage.getItem(STORAGE_KEY + '-updated') || 0);
      if (saved && (!draft.updated || stamp > draft.updated)) data = { ...data, ...JSON.parse(saved) };
    } catch { /* browser storage is optional */ }
    updateEdition();
    buildFields();
    runLocalChecks();
    await historyList();
    $('#autosave').textContent = '초안을 불러왔습니다. 입력하면 자동으로 저장됩니다.';
    await preview();
    runServerChecks();
  } catch (error) {
    toast('편집실을 불러오지 못했습니다: ' + error.message);
  }
})();
