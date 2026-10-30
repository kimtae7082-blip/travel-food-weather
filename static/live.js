const $ = s => document.querySelector(s);
const state = { category: 'all', region: '강원', audience: 'family', q: '', mode: 'live', page: 1 };
const labels = { stay: '머무는 곳', scenery: '풍경·산책', food: '음식점' };
let requestNumber = 0, weatherNumber = 0, priceNumber = 0;
function el(tag, cls, text) { const n = document.createElement(tag); if(cls) n.className=cls; if(text!==undefined) n.textContent=text; return n; }
function link(url, label) {
  if(!url) return null;
  try { if(!['http:', 'https:'].includes(new URL(url).protocol)) return null; } catch { return null; }
  const n=el('a','',label); n.href=url; n.target='_blank'; n.rel='noopener noreferrer'; return n;
}
function card(p) {
  const article=el('article','place-card'), picture=el('div',`card-picture ${p.category}`), image=el('img');
  image.src='/static/landscape.svg'; image.alt=''; image.loading='lazy';
  picture.append(image,el('span','category-badge',labels[p.category]),el('span','illustration-label','일러스트 · 현장 사진 아님'));
  const body=el('div','card-body');
  body.append(el('p','card-location',`${p.region} · ${p.city}`),el('h3','',p.name),el('p','card-description',p.description),el('p','card-tags',p.tags.split('·').map(t=>`#${t.trim()}`).join(' ')));
  const bottom=el('div','card-bottom'), button=el('button','detail-button','상세 정보 ↗');
  button.addEventListener('click',()=>details(p));
  bottom.append(el('span','',p.is_demo?'예시 · 이용 조건 미확인':'출처: 카카오 로컬'),button);
  body.append(bottom); article.append(picture,body); return article;
}
function details(p) {
  $('#detail-name').textContent=p.name; $('#detail-description').textContent=p.description;
  const facts=$('#detail-facts'); facts.replaceChildren();
  const rows=[['지역·주소',p.address||`${p.region} · ${p.city}`],['정보 구분',p.is_demo?'화면 확인용 예시 데이터':`${p.provider} 검색 결과 / 적합성 미검증`],['전화번호',p.phone||'미제공'],['영업·이용 상태',p.operating_status],['조회 시각',p.fetched_at||'미제공'],['최종 영업 확인일',p.checked_at||'별도 확인하지 않음'],['가격·예약','아래 날짜별 숙박 가격에서 별도 조회'],['이미지','직접 제작한 일러스트 / 현장 사진 아님']];
  rows.forEach(([k,v])=>facts.append(el('dt','',k),el('dd','',v)));
  const source=link(p.source_url,'카카오맵에서 원문 보기 ↗');
  if(source){const dd=el('dd');dd.append(source);facts.append(el('dt','','출처'),dd);}
  $('#detail').showModal();
}
async function loadWeather() {
  const request=++weatherNumber;
  $('#temperature').textContent='—'; $('#weather-status').textContent='불러오는 중';
  $('#weather-time').textContent='데이터 기준 시각: 미제공'; $('#weather-fetch').textContent='';
  try {
    const response=await fetch(`/api/weather?region=${encodeURIComponent(state.region)}`); if(!response.ok) throw new Error();
    const w=await response.json(); if(request!==weatherNumber)return;
    $('#weather-region').textContent=w.city?`${w.city} · ${w.region} 대표 지점`:'지역을 선택해 주세요';
    $('#temperature').textContent=w.temperature==null?'—':String(w.temperature);
    $('#weather-status').textContent=w.status==='live'?'현재 날씨 · 모델 추정값':w.status==='select_region'?'지역 선택 필요':'연결 실패';
    $('#weather-description').textContent=w.message;
    $('#weather-time').textContent=`데이터 기준: ${w.valid_at?.replace('T',' ')||'미제공'} (한국 시간)`;
    $('#weather-fetch').textContent=w.fetched_at?`조회: ${w.fetched_at.replace('T',' ')} · 10분 캐시`:'';
  } catch {if(request!==weatherNumber)return;$('#weather-status').textContent='연결 실패';$('#weather-description').textContent='날씨를 가져오지 못했어요. 장소 검색은 계속 이용할 수 있습니다.';}
}
async function loadResults() {
  const request=++requestNumber; $('#cards').setAttribute('aria-busy','true'); $('#error').hidden=true;
  $('#cards').replaceChildren(el('p','data-note','여행 정보를 불러오고 있어요…')); $('#empty').hidden=true; $('#result-count').textContent='';
  $('#next-page').hidden=true;$('#previous-page').hidden=true;
  $('#result-region').textContent=`${state.region==='전체'?'전국':state.region} · ${state.audience==='family'?'가족여행':'개인여행'}`;
  $('#tip-title').textContent=state.audience==='family'?'함께라서 더 편안하게':'혼자라서 더 자유롭게';
  $('#tip-text').textContent=state.audience==='family'?'가족 객실·유아 의자·보행 편의는 별도 확인이 필요합니다. 검색 결과를 가족 적합성 순으로 정렬하지 않습니다.':'1인 주문·개별 욕실·대중교통은 별도 확인이 필요합니다. 검색 결과를 개인 적합성 순으로 정렬하지 않습니다.';
  try {
    const response=await fetch(`/api/places?${new URLSearchParams(state)}`);if(!response.ok)throw new Error();
    const data=await response.json();if(request!==requestNumber)return;
    $('#cards').replaceChildren(...data.items.map(card));$('#empty').hidden=data.total!==0;
    $('#result-count').textContent=`${data.mode==='demo'?'예시 ':'현재 페이지 '}${data.total}곳`;
    $('#data-note').textContent=data.message;
    $('#empty-title').textContent=data.status==='needs_key'?'실제 장소 검색 키를 등록해 주세요':data.status==='unavailable'?'장소 서비스 연결을 확인해 주세요':'조건에 맞는 장소가 없어요';
    $('#empty-message').textContent=data.status==='needs_key'?'.env 파일에 카카오 REST API 키를 저장하면 다음 검색부터 반영됩니다. 화면만 확인하려면 위에서 예시 모드를 선택하세요.':data.message;
    $('#page-number').textContent=data.mode==='live'&&data.total?`${state.page}페이지`:'';
    $('#next-page').hidden=!data.has_more||state.page>=45;$('#previous-page').hidden=data.mode!=='live'||state.page<=1;
  } catch {if(request!==requestNumber)return;$('#cards').replaceChildren();$('#error').hidden=false;$('#error').textContent='정보를 불러오지 못했어요. 서버 실행 상태를 확인한 뒤 여행 검색을 다시 눌러 주세요.';}
  finally {if(request===requestNumber)$('#cards').setAttribute('aria-busy','false');}
}
function invalidatePrices(){priceNumber++;$('#price-results').replaceChildren();$('#price-message').textContent='조건이 바뀌었습니다. 날짜와 인원을 확인한 뒤 가격 조회를 눌러 주세요.';}
$('#search-form').addEventListener('submit',e=>{e.preventDefault();const previous=state.region;state.region=$('#region').value;state.audience=new FormData(e.currentTarget).get('audience');state.q=$('#keyword').value;state.page=1;loadResults();loadWeather();if(previous!==state.region)invalidatePrices();});
document.querySelectorAll('[data-category]').forEach(b=>b.addEventListener('click',()=>{state.category=b.dataset.category;state.page=1;document.querySelectorAll('[data-category]').forEach(n=>{n.classList.toggle('active',n===b);n.setAttribute('aria-pressed',String(n===b));});loadResults();}));
document.querySelectorAll('[data-region]').forEach(b=>b.addEventListener('click',()=>{$('#region').value=b.dataset.region;$('#keyword').value='';$('#search-form').requestSubmit();}));
$('#data-mode').addEventListener('change',()=>{state.mode=$('#data-mode').value;state.page=1;loadResults();});
$('#next-page').addEventListener('click',()=>{state.page++;loadResults();});$('#previous-page').addEventListener('click',()=>{state.page--;loadResults();});
$('#reset').addEventListener('click',()=>{state.category='all';state.region='전체';state.q='';state.page=1;$('#keyword').value='';$('#region').value='전체';document.querySelectorAll('[data-category]').forEach(b=>{b.classList.toggle('active',b.dataset.category==='all');b.setAttribute('aria-pressed',String(b.dataset.category==='all'));});loadResults();loadWeather();invalidatePrices();});
$('.close').addEventListener('click',()=>$('#detail').close());$('.close-detail').addEventListener('click',()=>$('#detail').close());
$('#region').addEventListener('change',invalidatePrices);
['checkin','checkout','adults','children'].forEach(id=>$(`#${id}`).addEventListener('input',invalidatePrices));
$('#price-form').addEventListener('submit',async e=>{
  e.preventDefault();const request=++priceNumber;$('#price-results').replaceChildren();$('#price-message').textContent='가격을 조회하고 있어요…';
  const params=new URLSearchParams({region:$('#region').value,checkin:$('#checkin').value,checkout:$('#checkout').value,adults:$('#adults').value,children:$('#children').value});
  try {
    const response=await fetch(`/api/hotel-prices?${params}`), data=await response.json();if(request!==priceNumber)return;
    if(!response.ok){$('#price-message').textContent=typeof data.detail==='string'?data.detail:'입력한 날짜와 인원을 확인해 주세요.';return;}
    $('#price-message').textContent=data.message+(data.area?` 검색 범위: ${data.area}. ${data.checkin} ~ ${data.checkout}, 성인 ${data.adults}명·아이 ${data.children.length}명·객실 1개. 조회 ${data.fetched_at}`:'');
    if(['live','sandbox'].includes(data.status)&&!data.items.length)$('#price-message').append(' 이 조건에서 표시할 원화 총액이 없습니다.');
    if(data.has_more)$('#price-message').append(' 일부 결과만 표시합니다.');
    data.items.forEach(item=>{const a=el('article','price-item');a.append(el('span','category-badge',data.status==='sandbox'?'테스트 가격':'Booking.com 조회'),el('h3','',item.name),el('strong','',`${new Intl.NumberFormat('ko-KR').format(Number(item.total))}원`),el('p','','전체 숙박 기간 · 1객실 · 입력한 인원 합계'));if(data.status==='live'){const source=link(item.url,'판매 페이지에서 조건 확인 ↗');if(source)a.append(source);}$('#price-results').append(a);});
  }catch{if(request===priceNumber)$('#price-message').textContent='가격 조회 연결에 실패했습니다. 잠시 후 다시 눌러 주세요.';}
});
async function initialize(){
  const today=new Date(), format=d=>d.toLocaleDateString('sv-SE',{timeZone:'Asia/Seoul'});
  $('#checkin').min=format(today);$('#checkout').min=format(today);$('#checkin').value=format(new Date(today.getTime()+86400000));$('#checkout').value=format(new Date(today.getTime()+172800000));
  try{const response=await fetch('/api/regions');if(!response.ok)throw new Error();const data=await response.json();data.regions.forEach(r=>{const option=el('option','',r);option.value=r;$('#region').append(option);});$('#region').value=state.region;loadResults();loadWeather();}
  catch{$('#cards').replaceChildren();$('#error').hidden=false;$('#error').textContent='지역 목록을 불러오지 못했어요. 서버 실행 후 새로고침해 주세요.';$('#cards').setAttribute('aria-busy','false');}
  try{const response=await fetch('/api/status');if(!response.ok)throw new Error();const s=await response.json();$('#service-status').textContent=s.places==='configured'?'실제 장소 검색 · 키 등록됨':'장소 검색 키 필요 · 날씨 API 연결 준비됨';$('#price-message').textContent=s.hotel_prices==='configured'?(s.hotel_environment==='production'?'키가 등록되었습니다. 날짜·인원을 입력해 실제 응답을 확인하세요.':'테스트 환경 키가 등록되었습니다. 실제 판매 가격이 아닙니다.'):'숙박 가격은 Booking.com Demand API 제휴 승인·API 키·Affiliate ID 등록 후 조회할 수 있습니다.';}
  catch{$('#service-status').textContent='연결 상태 확인 실패';$('#price-message').textContent='서비스 연결 상태를 확인하지 못했습니다.';}
}
initialize();
