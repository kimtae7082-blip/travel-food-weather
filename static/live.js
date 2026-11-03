const $ = s => document.querySelector(s);
const state = { category: 'all', region: '강원', audience: 'family', q: '', mode: 'live', page: 1 };
const labels = { stay: '머무는 곳', scenery: '풍경·산책', food: '음식점' };
let requestNumber = 0, weatherNumber = 0, hotelNumber = 0, detailNumber = 0;
function el(tag, cls, text) { const n = document.createElement(tag); if(cls) n.className=cls; if(text!==undefined) n.textContent=text; return n; }
function link(url, label) {
  if(!url) return null;
  try { if(!['http:', 'https:'].includes(new URL(url).protocol)) return null; } catch { return null; }
  const n=el('a','',label); n.href=url; n.target='_blank'; n.rel='noopener noreferrer'; return n;
}
function card(p) {
  const article=el('article','place-card'), picture=el('div',`card-picture place-photo ${p.category}`);
  const photo=p.photo;
  const attribution=el('div','photo-attribution');
  function placeholder(message){
    picture.querySelector('img')?.remove(); picture.classList.add('photo-missing');
    picture.querySelector('.photo-placeholder')?.remove();
    const fallback=el('img'); fallback.src='/static/landscape.svg'; fallback.alt='대체 풍경 일러스트 · 실제 장소 사진 아님'; picture.classList.add('photo-fallback'); picture.append(fallback,el('span','illustration-label','대체 일러스트 · 실제 장소 사진 아님')); 
  }
  if(!p.is_demo && photo?.status==='available' && photo.url){
    const image=el('img'); image.alt=`${p.name} · 제공기관 등록 사진 (촬영일 미제공)`;
    image.loading='lazy'; image.decoding='async'; image.referrerPolicy='no-referrer';
    let usedAlternative=false;
    image.addEventListener('error',()=>{
      if(!usedAlternative && photo.alternate_url && photo.alternate_url!==photo.url){usedAlternative=true;image.src=photo.alternate_url;return;}
      placeholder('사진을 불러오지 못했어요'); attribution.replaceChildren(el('span','','사진 연결 실패 · 직접 제작한 풍경 일러스트로 대체')); 
    });
    image.src=photo.url; picture.append(image);
    const source=link(photo.source_url,'사진: 한국관광공사 TourAPI');
    const license=link(photo.license_url,photo.license_label);
    if(source)attribution.append(source);if(license)attribution.append(license);
    attribution.append(el('span','','촬영일 미제공'));
  }else{
    placeholder(p.is_demo?'예시 데이터 · 실제 사진 없음':photo?.caption||'사진 미등록');
    attribution.append(el('span','',p.is_demo?'예시 데이터 · 직접 제작한 풍경 일러스트':`${photo?.caption||'사진 미등록'} · 풍경 일러스트로 대체`));
  }
  picture.append(el('span','category-badge',labels[p.category]));
  const body=el('div','card-body');
  body.append(el('p','card-location',`${p.region} · ${p.city}`),el('h3','',p.name),el('p','card-description',p.description),el('p','card-tags',p.tags.split('·').map(t=>`#${t.trim()}`).join(' ')));
  const bottom=el('div','card-bottom'), button=el('button','detail-button','상세 정보 ↗');
  button.addEventListener('click',event=>{event.stopPropagation();details(p);});
  if(p.category!=='stay'){
    article.classList.add('clickable-card');article.tabIndex=0;article.setAttribute('aria-label',`${p.name} 상세정보 열기`);
    article.addEventListener('click',event=>{if(!event.target.closest('a,button'))details(p);});
    article.addEventListener('keydown',event=>{if(event.target===article&&(event.key==='Enter'||event.key===' ')){event.preventDefault();details(p);}});
  }
  bottom.append(el('span','',p.is_demo?'예시 · 이용 조건 미확인':'출처: 한국관광공사'));if(p.category!=='stay')bottom.append(button);
  if(p.category==='stay'){const more=el('button','outline-button stay-more','더보기');more.addEventListener('click',()=>stayMore(p));body.append(more);if(!p.is_demo){const app=link('https://www.agoda.com/ko-kr/','아고다 열기 ↗');if(app)body.append(app);}}
  body.append(bottom); article.append(picture,attribution,body); return article;
}
function details(p) {
  if(p.category==='stay'){stayMore(p);return;}
  $('#detail').classList.remove('stay-dialog');$('#stay-extra').hidden=true;$('#stay-extra').replaceChildren();
  $('#detail-name').textContent=p.name; $('#detail-description').textContent=p.description;
  const facts=$('#detail-facts'); facts.replaceChildren();
  const rows=[['지역·주소',p.address||`${p.region} · ${p.city}`],['정보 구분',p.is_demo?'화면 확인용 예시 데이터':`${p.provider} 검색 결과 / 적합성 미검증`],['전화번호',p.phone||'미제공'],['영업·이용 상태',p.operating_status],['조회 시각',p.fetched_at||'미제공'],['최종 영업 확인일',p.checked_at||'별도 확인하지 않음'],['공공데이터 ID',p.content_id||'예시'],['공공데이터 수정시각',p.provider_modified_at||'미제공'],['가격·예약','아래 숙소 앱 연결에서 확인'],['사진',p.photo?.status==='available'?`한국관광공사 TourAPI 제공 / ${p.photo.license_label}`:'이용 가능한 사진 미제공'],['사진 촬영일','미제공 · 최신 사진 여부 미확인']];
  rows.forEach(([k,v])=>facts.append(el('dt','',k),el('dd','',v)));
  const source=link(p.source_url,'공식 데이터 제공 안내 ↗');
  if(source){const dd=el('dd');dd.append(source);facts.append(el('dt','','출처'),dd);}
  if(p.photo?.status==='available'){
    const original=link(p.photo.url,'제공 원본 사진 열기 ↗');
    const license=link(p.photo.license_url,p.photo.license_label);
    if(original){const dd=el('dd');dd.append(original);facts.append(el('dt','','원본 사진'),dd);}
    if(license){const dd=el('dd');dd.append(license);facts.append(el('dt','','사진 이용 조건'),dd);}
  }
  $('#detail').showModal();
}

function stayText(value){return !value||value==='미제공'?'등록된 정보가 없어요':String(value).replaceAll('미제공','등록된 정보가 없어요');}
function staySection(title){const section=el('section','stay-section');section.append(el('h3','',title));$('#stay-extra').append(section);return section;}
async function stayMore(p){
  const request=++detailNumber, dialog=$('#detail');dialog.classList.add('stay-dialog');
  $('#detail-name').textContent=p.name;$('#detail-description').textContent='숙소 소개와 이용 안내, 주변 정보를 불러오고 있어요…';
  $('#detail-facts').replaceChildren();$('#stay-extra').replaceChildren();$('#stay-extra').hidden=false;
  if(!dialog.open)dialog.showModal();
  if(p.is_demo||!p.content_id){$('#detail-description').textContent='이 카드는 가상 숙소 예시입니다. 실제 숙소 소개·주차·주변 정보는 실제 검색 모드에서 확인할 수 있습니다.';return;}
  try{
    const response=await fetch(`/api/stays/${encodeURIComponent(p.content_id)}`);if(!response.ok)throw new Error();
    const data=await response.json();if(request!==detailNumber||!dialog.open)return;
    if(!['live','partial'].includes(data.status))throw new Error(data.message||'상세 정보 미제공');
    $('#detail-name').textContent=data.name||p.name;$('#detail-description').textContent=stayText(data.overview);
    const basic=staySection('숙소 기본 정보');const basics=el('dl','stay-fields');
    [['주소',data.address||'미제공'],['문의 전화',data.phone||'미제공']].forEach(([k,v])=>basics.append(el('dt','',k),el('dd','',stayText(v))));basic.append(basics);
    const facilities=staySection('주차 · 객실 · 이용 안내');const fields=el('dl','stay-fields');
    data.fields.forEach(field=>fields.append(el('dt','',field.label),el('dd','',stayText(field.value))));facilities.append(fields);
    [['attractions','근처 볼거리'],['restaurants','근처 음식점']].forEach(([key,title])=>{
      const section=staySection(title), group=data.nearby[key];
      section.append(el('p','data-note',stayText(group?.message)));
      if(!group||!group.items.length){section.append(el('p','nearby-empty',group?.status==='live'?'반경 5km 안에 조회된 등록 정보가 없습니다.':group?.status==='no_coordinates'?'숙소 위치 좌표가 제공되지 않았습니다.':'주변 정보를 불러오지 못했습니다.'));return;}
      section.append(el('p','data-note','길찾기는 숙소를 출발지로 Google 지도에서 열립니다. 사진 촬영일과 최신 여부는 확인되지 않았습니다.'));
      const list=el('ul','nearby-list');
      group.items.forEach(item=>{
        const li=el('li','nearby-item'), media=el('div','nearby-media'), info=el('div','nearby-info'), photo=item.photo;
        function fallback(){media.replaceChildren();const image=el('img');image.src='/static/landscape.svg';image.alt='대체 일러스트 · 실제 장소 사진 아님';media.append(image,el('span','nearby-photo-note','대체 일러스트'));}
        if(photo?.status==='available'&&photo.url){
          const image=el('img');image.src=photo.url;image.alt=`${item.name} 등록 사진 · 촬영일 미확인`;image.loading='lazy';image.referrerPolicy='no-referrer';
          let alternative=false;image.addEventListener('error',()=>{if(!alternative&&photo.alternate_url&&photo.alternate_url!==photo.url){alternative=true;image.src=photo.alternate_url;}else fallback();});media.append(image);
          const credit=el('div','nearby-credit');const source=link(photo.source_url,'사진: 한국관광공사'),license=link(photo.license_url,photo.license_label);if(source)credit.append(source);if(license)credit.append(license);media.append(credit);
        }else fallback();
        info.append(el('strong','',item.name));
        if(item.distance_m!==null){const distance=item.distance_m<1000?`${item.distance_m}m`:`${(item.distance_m/1000).toFixed(1)}km`;info.append(el('span','distance',`직선 약 ${distance}`));}
        info.append(el('p','',item.address||'등록된 주소가 없어요'));
        const route=new URL('https://www.google.com/maps/dir/');route.searchParams.set('api','1');route.searchParams.set('origin',`${data.name||p.name} ${data.address||p.address||''}`.trim());route.searchParams.set('destination',`${item.name} ${item.address||''}`.trim());
        const directions=link(route.href,'길찾기 ↗');directions.className='nearby-directions';directions.setAttribute('aria-label',`숙소에서 ${item.name}까지 길찾기 · Google 지도 새 창`);info.append(directions);
        li.append(media,info);list.append(li);
      });section.append(list);
    });
    if(data.warnings.length){const warning=staySection('일부 정보 조회 안내');warning.append(el('p','',data.warnings.join(' · ')));}
    const facts=$('#detail-facts');[['출처','한국관광공사 TourAPI'],['조회 시각',data.fetched_at],['공공데이터 수정시각',data.provider_modified_at||'미제공'],['최종 영업 확인일','별도 확인하지 않음']].forEach(([k,v])=>facts.append(el('dt','',k),el('dd','',stayText(v))));
    $('#stay-extra').append(el('p','data-note',data.message));
  }catch(error){
    if(request!==detailNumber||!dialog.open)return;
    $('#detail-description').textContent=error.message&&error.message!=='Failed to fetch'?stayText(error.message):'숙소 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';
    const retry=el('button','outline-button','다시 불러오기');retry.addEventListener('click',()=>stayMore(p));$('#stay-extra').append(retry);
  }
}
$('#detail').addEventListener('close',()=>{detailNumber++;});

async function loadWeather() {
  const request=++weatherNumber;
  $('#temperature').textContent='—'; $('#weather-status').textContent='불러오는 중';
  $('#weather-time').textContent='데이터 기준 시각: 미제공'; $('#weather-fetch').textContent='';
  try {
    const response=await fetch(`/api/weather?region=${encodeURIComponent(state.region)}`); if(!response.ok) throw new Error();
    const w=await response.json(); if(request!==weatherNumber)return;
    $('#weather-region').textContent=w.city?`${w.city} · ${w.region} 대표 지점`:'지역을 선택해 주세요';
    $('#temperature').textContent=w.temperature==null?'—':String(w.temperature);
    $('#weather-status').textContent=w.status==='live'?'OpenWeather 현재 날씨':w.status==='needs_key'?'API 키 등록 필요':w.status==='select_region'?'지역 선택 필요':'연결 실패';
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
    $('#empty-message').textContent=data.status==='needs_key'?'.env 파일의 TOUR_API_KEY에 무료 TourAPI 인증키를 저장하면 다음 검색부터 반영됩니다. 화면만 확인하려면 위에서 예시 모드를 선택하세요.':data.message;
    $('#page-number').textContent=data.mode==='live'&&data.total?`${state.page}페이지`:'';
    $('#next-page').hidden=!data.has_more||state.page>=45;$('#previous-page').hidden=data.mode!=='live'||state.page<=1;
  } catch {if(request!==requestNumber)return;$('#cards').replaceChildren();$('#error').hidden=false;$('#error').textContent='정보를 불러오지 못했어요. 서버 실행 상태를 확인한 뒤 여행 검색을 다시 눌러 주세요.';}
  finally {if(request===requestNumber)$('#cards').setAttribute('aria-busy','false');}
}
function invalidatePrices(){loadHotelLinks($('#region').value);}
$('#search-form').addEventListener('submit',e=>{e.preventDefault();const previous=state.region;state.region=$('#region').value;state.audience=new FormData(e.currentTarget).get('audience');state.q=$('#keyword').value;state.page=1;loadResults();loadWeather();if(previous!==state.region)invalidatePrices();});
document.querySelectorAll('[data-category]').forEach(b=>b.addEventListener('click',()=>{state.category=b.dataset.category;state.page=1;document.querySelectorAll('[data-category]').forEach(n=>{n.classList.toggle('active',n===b);n.setAttribute('aria-pressed',String(n===b));});loadResults();}));
document.querySelectorAll('[data-region]').forEach(b=>b.addEventListener('click',()=>{$('#region').value=b.dataset.region;$('#keyword').value='';$('#search-form').requestSubmit();}));
$('#data-mode').addEventListener('change',()=>{state.mode=$('#data-mode').value;state.page=1;loadResults();});
$('#next-page').addEventListener('click',()=>{state.page++;loadResults();});$('#previous-page').addEventListener('click',()=>{state.page--;loadResults();});
$('#reset').addEventListener('click',()=>{state.category='all';state.region='전체';state.q='';state.page=1;$('#keyword').value='';$('#region').value='전체';document.querySelectorAll('[data-category]').forEach(b=>{b.classList.toggle('active',b.dataset.category==='all');b.setAttribute('aria-pressed',String(b.dataset.category==='all'));});loadResults();loadWeather();invalidatePrices();});
$('.close').addEventListener('click',()=>$('#detail').close());$('.close-detail').addEventListener('click',()=>$('#detail').close());
$('#region').addEventListener('change',invalidatePrices);
async function copyText(text){
  try {await navigator.clipboard.writeText(text);$('#price-message').textContent='검색어를 복사했습니다. 아고다에서 붙여넣고 날짜·인원을 입력해 주세요.';}
  catch {$('#hotel-query').value=text;$('#hotel-query').focus();$('#hotel-query').select();$('#price-message').textContent='자동 복사가 되지 않았습니다. 선택된 검색어를 Ctrl+C로 복사하세요.';}
}
$('#copy-hotel-query').addEventListener('click',()=>copyText($('#hotel-query').value));
async function loadHotelLinks(region){
  const request=++hotelNumber;
  try {const response=await fetch(`/api/hotel-links?region=${encodeURIComponent(region)}`);if(!response.ok)throw new Error();const data=await response.json();if(request!==hotelNumber)return;$('#hotel-query').value=data.query;$('#price-message').textContent=data.message;}
  catch {if(request===hotelNumber)$('#price-message').textContent='안내를 불러오지 못했어요. 아고다에서 지역·날짜·인원을 직접 검색할 수 있습니다.';}
}
async function initialize(){
  try{const response=await fetch('/api/regions');if(!response.ok)throw new Error();const data=await response.json();data.regions.forEach(r=>{const option=el('option','',r);option.value=r;$('#region').append(option);});$('#region').value=state.region;loadResults();loadWeather();loadHotelLinks(state.region);}
  catch{$('#cards').replaceChildren();$('#error').hidden=false;$('#error').textContent='지역 목록을 불러오지 못했어요. 서버 실행 후 새로고침해 주세요.';$('#cards').setAttribute('aria-busy','false');}
  try{const response=await fetch('/api/status');if(!response.ok)throw new Error();const s=await response.json();$('#service-status').textContent=`OpenWeather ${s.weather==='configured'?'키 등록됨':'키 필요'} · TourAPI ${s.places==='configured'?'키 등록됨':'키 필요'}`;}
  catch{$('#service-status').textContent='연결 상태 확인 실패';}
}
initialize();
