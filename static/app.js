const $ = (selector) => document.querySelector(selector);
const state = { category: 'all', region: '강원', audience: 'family', q: '' };
const labels = { stay: '머무는 곳', scenery: '풍경·산책', food: '음식 탐방' };
let requestNumber = 0;
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function card(place) {
  const article = element('article', 'place-card');
  const picture = element('div', `card-picture ${place.category}`);
  const image = element('img'); image.src = '/static/landscape.svg'; image.alt = ''; image.loading = 'lazy';
  picture.append(image, element('span', 'category-badge', labels[place.category]), element('span', 'illustration-label', '예시 일러스트 · 현장 사진 아님'));
  const body = element('div', 'card-body');
  body.append(element('p', 'card-location', `${place.region} · ${place.city}`), element('h3', '', place.name), element('p', 'card-description', place.description), element('p', 'card-tags', place.tags.split('·').map(t => `#${t.trim()}`).join(' ')));
  const bottom = element('div', 'card-bottom');
  const button = element('button', 'detail-button', '상세 정보 ↗');
  button.addEventListener('click', () => showDetails(place));
  bottom.append(element('span', '', place.category === 'scenery' ? '이용 조건 미확인' : '가상 업체 · 예시'), button);
  body.append(bottom); article.append(picture, body); return article;
}
function showDetails(place) {
  $('#detail-name').textContent = place.name;
  $('#detail-description').textContent = place.description;
  const facts = $('#detail-facts'); facts.replaceChildren();
  const rows = [['지역', `${place.region} · ${place.city}`], ['정보 구분', place.category === 'scenery' ? '실제 명소 이름을 사용한 탐방 후보 예시' : '화면 구성용 가상 업체'], ['운영·이용 상태', place.operating_status], ['최종 운영 확인일', place.checked_at || '미확인'], ['업체별 출처', place.source_url || '미등록'], ['가격·예약', '서비스 미연결'], ['이미지', '직접 제작한 일러스트 / 현장 사진 아님']];
  rows.forEach(([key,value]) => facts.append(element('dt','',key),element('dd','',value)));
  $('#detail').showModal();
}
async function loadResults() {
  const request = ++requestNumber;
  $('#cards').setAttribute('aria-busy', 'true'); $('#error').hidden = true;
  $('#cards').replaceChildren(element('p','data-note','여행 정보를 불러오고 있어요…'));
  $('#empty').hidden = true; $('#result-count').textContent = '';
  const params = new URLSearchParams(state);
  try {
    const [response, weatherResponse] = await Promise.all([fetch(`/api/places?${params}`), fetch(`/api/weather?region=${encodeURIComponent(state.region)}`)]);
    if (!response.ok || !weatherResponse.ok) throw new Error('서버 응답 오류');
    const [data, weather] = await Promise.all([response.json(), weatherResponse.json()]);
    if (request !== requestNumber) return;
    $('#cards').replaceChildren(...data.items.map(card)); $('#empty').hidden = data.total !== 0;
    $('#result-count').textContent = `예시 ${data.total}곳`;
    $('#result-region').textContent = `${state.region === '전체' ? '전국' : state.region} · ${state.audience === 'family' ? '가족여행' : '개인여행'}`;
    $('#weather-region').textContent = weather.region === '전체' ? '전국 · 지역을 선택해 주세요' : weather.region;
    $('#tip-title').textContent = state.audience === 'family' ? '함께라서 더 편안하게' : '혼자라서 더 자유롭게';
    $('#tip-text').textContent = state.audience === 'family' ? '가족 숙소는 추가 인원 요금까지, 산책길은 계단과 휴식 공간까지 확인해 보세요.' : '1인 주문이 가능한 식당인지, 숙소에서 대중교통으로 이동할 수 있는지 확인해 보세요.';
  } catch (error) {
    if (request !== requestNumber) return;
    $('#cards').replaceChildren(); $('#error').hidden = false;
    $('#error').textContent = '정보를 불러오지 못했어요. 서버 실행 상태를 확인한 뒤 여행 검색을 다시 눌러 주세요.';
  } finally { if (request === requestNumber) $('#cards').setAttribute('aria-busy','false'); }
}
$('#search-form').addEventListener('submit', event => {event.preventDefault(); state.region = $('#region').value; state.audience = new FormData(event.currentTarget).get('audience'); state.q = $('#keyword').value; loadResults();});
document.querySelectorAll('[data-category]').forEach(button => button.addEventListener('click', () => {
  state.category = button.dataset.category;
  document.querySelectorAll('[data-category]').forEach(b => {b.classList.toggle('active', b === button);b.setAttribute('aria-pressed', String(b === button));}); loadResults();
}));
document.querySelectorAll('[data-region]').forEach(button => button.addEventListener('click', () => {$('#region').value = button.dataset.region; $('#keyword').value = ''; $('#search-form').requestSubmit();}));
$('#reset').addEventListener('click', () => {state.category = 'all';$('#keyword').value = '';$('#region').value = '전체';document.querySelector('[data-category="all"]').click();$('#search-form').requestSubmit();});
$('.close').addEventListener('click', () => $('#detail').close()); $('.close-detail').addEventListener('click', () => $('#detail').close());
async function initialize() {
  try {
    const response = await fetch('/api/regions'); if (!response.ok) throw new Error();
    const data = await response.json();
    data.regions.forEach(region => {const option = element('option','',region);option.value=region;$('#region').append(option);});
    $('#region').value = state.region; await loadResults();
  } catch (error) {$('#cards').replaceChildren();$('#error').hidden=false;$('#error').textContent='지역 목록을 불러오지 못했어요. 서버를 실행한 뒤 페이지를 새로고침해 주세요.';$('#cards').setAttribute('aria-busy','false');}
}
initialize();
