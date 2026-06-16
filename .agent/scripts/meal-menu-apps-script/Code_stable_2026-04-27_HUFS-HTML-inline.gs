/**
 * 매주 일요일 오전 주간 급식표 메일 발송기
 * - 경희대 푸른솔(khucoop.com/37): 페이지 내 식단표 이미지 1장 첨부
 * - 경희대 청운관(khucoop.com/36): 페이지 내 식단표 이미지 1장 첨부
 * - 한국외대 인문관(hufs.ac.kr/hufs/11318): 주간 메뉴 HTML 테이블을 임시 Google Sheets에 그려 PNG로 export 후 첨부
 */

const CONFIG = {
  recipient: 'kmjy98@gmail.com',
  timezone: 'Asia/Seoul',
  senderName: '주간 급식표 봇',
  sources: [
    { key: 'khu_pureunsol', name: '경희대 푸른솔 식당', url: 'https://khucoop.com/37', type: 'khu' },
    { key: 'khu_cheongwoon', name: '경희대 청운관 식당', url: 'https://khucoop.com/36', type: 'khu' },
    { key: 'hufs_inmun', name: '한국외대 인문관 식당', url: 'https://www.hufs.ac.kr/hufs/11318/subview.do', type: 'hufs', cafId: 'h101' }
  ]
};

/** 메인: KHU는 PNG 첨부, HUFS는 HTML 표를 메일 본문에 inline 삽입 */
function sendWeeklyMealMenu() {
  const tz = CONFIG.timezone;
  const today = new Date();
  const ymd = Utilities.formatDate(today, tz, 'yyyy-MM-dd');
  const subject = '[주간 급식표] ' + ymd + ' 주';

  const attachments = [];
  const lines = [];
  const htmlSections = [];
  lines.push(ymd + ' 주간 급식표입니다.');
  lines.push('');
  lines.push('───────────────────────────');
  htmlSections.push('<p>' + ymd + ' 주간 급식표입니다.</p>');

  for (let i = 0; i < CONFIG.sources.length; i++) {
    const src = CONFIG.sources[i];
    lines.push('');
    lines.push('[' + (i + 1) + '] ' + src.name);
    lines.push('출처: ' + src.url);
    htmlSections.push('<hr>');
    htmlSections.push('<h3>[' + (i + 1) + '] ' + escapeHtml_(src.name) + '</h3>');
    htmlSections.push('<p>출처: <a href="' + escapeHtml_(src.url) + '">' + escapeHtml_(src.url) + '</a></p>');

    try {
      if (src.type === 'khu') {
        const blob = fetchKhuMenuImage_(src);
        attachments.push(blob);
        lines.push('상태: 첨부 완료 (' + blob.getName() + ')');
        htmlSections.push('<p>상태: 첨부 완료 (' + escapeHtml_(blob.getName()) + ')</p>');
      } else if (src.type === 'hufs') {
        const tableHtml = fetchHufsMenuHtml_(src);
        lines.push('상태: 본문 inline');
        htmlSections.push(tableHtml);
      } else {
        throw new Error('알 수 없는 소스 타입: ' + src.type);
      }
    } catch (e) {
      Logger.log('[' + src.key + '] 실패: ' + e.message + '\n' + (e.stack || ''));
      lines.push('상태: 실패 — ' + e.message);
      htmlSections.push('<p style="color:#b91c1c">상태: 실패 — ' + escapeHtml_(e.message) + '</p>');
    }
  }

  lines.push('');
  lines.push('───────────────────────────');
  lines.push('자동 발송 (Google Apps Script).');
  htmlSections.push('<hr><p style="color:#666;font-size:12px">자동 발송 (Google Apps Script).</p>');

  GmailApp.sendEmail(CONFIG.recipient, subject, lines.join('\n'), {
    name: CONFIG.senderName,
    attachments: attachments,
    htmlBody: htmlSections.join('\n')
  });
}

/* =========================================================
 *  KHU (imweb 기반 페이지) — org_image 클래스 첫 이미지를 첨부
 * ========================================================= */

function fetchKhuMenuImage_(src) {
  // imweb이 Apps Script 공유 IP에 강한 rate-limit를 걸어 페이지 자체가 quota exceeded로 막히는 케이스 방지.
  // 매주 같은 이미지이므로 ISO week 키로 Drive에 캐시.
  const cached = cachedKhuBlob_(src);
  if (cached) return cached;

  const html = httpGet_(src.url);
  // <img ... class="... org_image..." ... src="..." />
  const imgTag = html.match(/<img[^>]*\bclass="[^"]*\borg_image\b[^"]*"[^>]*>/i);
  if (!imgTag) throw new Error('org_image 태그를 찾지 못했습니다');
  const srcMatch = imgTag[0].match(/\bsrc="([^"]+)"/);
  if (!srcMatch) throw new Error('img src 속성 미발견');
  let imageUrl = srcMatch[1];
  if (imageUrl.indexOf('//') === 0) imageUrl = 'https:' + imageUrl;
  if (imageUrl.indexOf('/') === 0) imageUrl = 'https://khucoop.com' + imageUrl;

  // imweb CDN(cdn.imweb.me)이 Apps Script 공유 IP에 bandwidth quota를 때리는 경우가 있어
  // 백오프 재시도 + 일반 브라우저 UA로 봇 탐지 우회
  const browserUA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    + '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
  const backoffsMs = [5000, 15000, 45000];
  let lastErr = null;
  for (let attempt = 0; attempt < backoffsMs.length; attempt++) {
    try {
      const resp = UrlFetchApp.fetch(imageUrl, {
        muteHttpExceptions: true,
        followRedirects: true,
        headers: {
          'User-Agent': browserUA,
          'Referer': src.url,
          'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
          'Accept-Language': 'ko,en;q=0.8'
        }
      });
      const code = resp.getResponseCode();
      const ct = (resp.getHeaders()['Content-Type'] || resp.getHeaders()['content-type'] || '').toString();
      if (code === 200 && ct.indexOf('image/') === 0) {
        const blob = resp.getBlob();
        const extMatch = imageUrl.match(/\.(png|jpe?g|gif|webp)(\?|$)/i);
        const ext = extMatch ? extMatch[1].toLowerCase() : 'png';
        blob.setName(src.key + '.' + ext);
        if (attempt > 0) Logger.log('[' + src.key + '] 재시도 #' + attempt + ' 성공');
        try { saveKhuBlobToCache_(src, blob); }
        catch (e) { Logger.log('[' + src.key + '] 캐시 저장 실패(무시): ' + e.message); }
        return blob;
      }
      const body = resp.getContentText().substring(0, 200);
      lastErr = new Error('이미지 응답 code=' + code + ', Content-Type=' + ct + ', 본문: ' + body);
      Logger.log('[' + src.key + '] 시도 ' + (attempt + 1) + '/3 실패: ' + lastErr.message);
    } catch (e) {
      lastErr = e;
      Logger.log('[' + src.key + '] 시도 ' + (attempt + 1) + '/3 예외: ' + e.message);
    }
    if (attempt < backoffsMs.length - 1) {
      Logger.log('[' + src.key + '] ' + (backoffsMs[attempt] / 1000) + '초 후 재시도');
      Utilities.sleep(backoffsMs[attempt]);
    }
  }
  // 모든 시도 실패 시: 가장 최근 KHU 캐시(전주 등)라도 stale fallback으로 첨부
  const stale = mostRecentKhuCacheBlob_(src);
  if (stale) {
    Logger.log('[' + src.key + '] 라이브 fetch 모두 실패 → stale 캐시 사용: ' + stale.getName());
    return stale;
  }
  throw lastErr || new Error('알 수 없는 fetch 실패');
}

/* =========================================================
 *  KHU 이미지 Drive 캐시 (ISO week 키)
 * ========================================================= */

const CACHE_FOLDER_NAME = 'meal-menu-cache';

function getCacheFolder_() {
  const it = DriveApp.getFoldersByName(CACHE_FOLDER_NAME);
  return it.hasNext() ? it.next() : DriveApp.createFolder(CACHE_FOLDER_NAME);
}

function isoWeekKey_(date, tz) {
  // 'YYYY' = ISO week-based year, 'ww' = ISO week number
  const y = Utilities.formatDate(date, tz, 'YYYY');
  const w = Utilities.formatDate(date, tz, 'ww');
  return y + '-W' + w;
}

function cacheFileNameForKhu_(src) {
  const week = isoWeekKey_(new Date(), CONFIG.timezone);
  return src.key + '_' + week + '.png';
}

function cachedKhuBlob_(src) {
  const folder = getCacheFolder_();
  const fileName = cacheFileNameForKhu_(src);
  const it = folder.getFilesByName(fileName);
  if (!it.hasNext()) return null;
  const f = it.next();
  Logger.log('[' + src.key + '] 캐시 사용 (Drive: ' + fileName + ')');
  return f.getBlob().setName(fileName);
}

function saveKhuBlobToCache_(src, blob) {
  const folder = getCacheFolder_();
  const fileName = cacheFileNameForKhu_(src);
  // 같은 이름 파일이 이미 있으면 (race) 그대로 두기
  if (folder.getFilesByName(fileName).hasNext()) return;
  folder.createFile(blob.copyBlob().setName(fileName));
  Logger.log('[' + src.key + '] 캐시 저장: ' + fileName);
}

function mostRecentKhuCacheBlob_(src) {
  const folder = getCacheFolder_();
  // src.key 접두사로 시작하는 파일들 중 가장 최근 것
  const it = folder.getFiles();
  let best = null;
  let bestTime = 0;
  while (it.hasNext()) {
    const f = it.next();
    if (f.getName().indexOf(src.key + '_') !== 0) continue;
    const t = f.getLastUpdated().getTime();
    if (t > bestTime) { bestTime = t; best = f; }
  }
  return best ? best.getBlob().setName(best.getName()) : null;
}

/* =========================================================
 *  HUFS — 주간 메뉴 HTML 테이블 → 메일 본문 inline HTML
 * ========================================================= */

function fetchHufsMenuHtml_(src) {
  // 1) 초기 페이지에서 폼 파라미터 추출
  const pageHtml = httpGet_(src.url);
  const params = parseHufsFormParams_(pageHtml);
  if (!params.year || !params.month || !params.weekFirst || !params.weekLast) {
    throw new Error('HUFS 폼 파라미터 추출 실패: ' + JSON.stringify(params));
  }

  // 2) AJAX 엔드포인트 POST
  const menuHtml = UrlFetchApp.fetch('https://www.hufs.ac.kr/cafeteria/hufs/1/getMenu', {
    method: 'post',
    payload: {
      selCafId: src.cafId || 'h101',
      selWeekFirstDay: params.weekFirst,
      selWeekLastDay: params.weekLast,
      selYear: params.year,
      selMonth: params.month
    },
    muteHttpExceptions: true,
    followRedirects: true,
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; MealMenuBot/1.0)',
      'X-Requested-With': 'XMLHttpRequest',
      'Referer': src.url
    }
  }).getContentText();

  // 3) 메뉴 테이블 → 2D 배열
  const grid = parseHufsMenuTable_(menuHtml);
  if (!grid || grid.length < 2) throw new Error('HUFS 메뉴 테이블 파싱 결과가 비어 있습니다');

  // 4) 2D 배열 → 메일 본문 inline용 HTML 표
  return renderGridAsHtml_(grid);
}

function parseHufsFormParams_(html) {
  const findInputValue = function (id) {
    const re = new RegExp('<input[^>]*\\bid="' + id + '"[^>]*>', 'i');
    const m = html.match(re);
    if (!m) return null;
    const vm = m[0].match(/\bvalue="([^"]*)"/);
    return vm ? vm[1] : null;
  };
  return {
    year: findInputValue('year'),
    month: findInputValue('month'),
    weekFirst: findInputValue('selWeekFirstDay'),
    weekLast: findInputValue('selWeekLastDay')
  };
}

function parseHufsMenuTable_(html) {
  // <script> 제거
  let h = html.replace(/<script[\s\S]*?<\/script>/gi, '');

  // 날짜 헤더 추출
  const dateRe = /<span[^>]*\bclass="date"[^>]*\bid="date_(\d{4}-\d{2}-\d{2})"[^>]*>([^<]+)<\/span>/g;
  const dates = [];
  let dm;
  while ((dm = dateRe.exec(h)) !== null) {
    // 텍스트 헤더 + (요일은 JS로 채워짐) → ISO 날짜에서 요일 계산
    const iso = dm[1];
    const label = dm[2].trim();
    dates.push(label + ' ' + isoDayLabel_(iso));
  }
  if (dates.length === 0) throw new Error('날짜 헤더 추출 실패');

  const rows = [];
  rows.push(['요일/메뉴'].concat(dates));

  // 모든 <tr> 추출
  const trRe = /<tr\b[^>]*>([\s\S]*?)<\/tr>/gi;
  let trMatch;
  while ((trMatch = trRe.exec(h)) !== null) {
    const rowHtml = trMatch[1];
    if (!/<th\b/i.test(rowHtml)) continue;
    const thMatch = rowHtml.match(/<th\b[^>]*>([\s\S]*?)<\/th>/i);
    if (!thMatch) continue;
    const mealRaw = stripHtml_(thMatch[1]).replace(/\s+/g, '');
    if (!/조식|중식|석식|점심|저녁|아침|간식/.test(mealRaw)) continue;

    // 헤더 셀 정리: "조식(08:00~10:00)" 등
    const meal = mealRaw
      .replace(/(\d{1,2}:\d{2})~(\d{1,2}:\d{2})/, ' ($1~$2)')
      .replace(/^([조중석]식|점심|저녁|아침|간식)/, '$1');

    // <td> 추출
    const tds = [];
    const tdRe = /<td\b[^>]*>([\s\S]*?)<\/td>/gi;
    let tdMatch;
    while ((tdMatch = tdRe.exec(rowHtml)) !== null) {
      tds.push(parseHufsCell_(tdMatch[1]));
    }
    rows.push([meal].concat(tds));
  }

  return rows;
}

function parseHufsCell_(cellHtml) {
  if (/\bno-menu\b/i.test(cellHtml)) return '—';
  const items = [];
  const liRe = /<li\b[^>]*>([\s\S]*?)<\/li>/gi;
  let m;
  while ((m = liRe.exec(cellHtml)) !== null) {
    const t = stripHtml_(m[1]).trim();
    if (t && t !== ' ') items.push(t);
  }
  let result = items.join('\n');
  const calMatch = cellHtml.match(/<p[^>]*\bclass="calorie"[^>]*>([\s\S]*?)<\/p>/i);
  const payMatch = cellHtml.match(/<p[^>]*\bclass="pay"[^>]*>([\s\S]*?)<\/p>/i);
  if (calMatch) result += (result ? '\n' : '') + '[' + stripHtml_(calMatch[1]).trim() + ']';
  if (payMatch) result += (result ? '\n' : '') + stripHtml_(payMatch[1]).trim();
  return result || '—';
}

function isoDayLabel_(iso) {
  const week = ['(일)', '(월)', '(화)', '(수)', '(목)', '(금)', '(토)'];
  const d = new Date(iso + 'T00:00:00+09:00');
  return week[d.getDay()];
}

function stripHtml_(s) {
  return s
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .trim();
}

/* =========================================================
 *  2D 배열 → 메일 본문 inline용 HTML 표
 * ========================================================= */

function renderGridAsHtml_(grid) {
  const headerRow = grid[0] || [];
  const bodyRows = grid.slice(1);
  let html = '<table style="border-collapse:collapse;width:100%;font-size:12px;'
    + 'font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:8px 0;">';
  html += '<thead><tr>';
  for (let c = 0; c < headerRow.length; c++) {
    html += '<th style="border:1px solid #888;padding:6px 8px;background:#fde68a;'
      + 'text-align:center;">' + escapeHtml_(String(headerRow[c])) + '</th>';
  }
  html += '</tr></thead><tbody>';
  for (let r = 0; r < bodyRows.length; r++) {
    const row = bodyRows[r];
    html += '<tr>';
    for (let c = 0; c < row.length; c++) {
      const isLabel = c === 0;
      const bg = isLabel ? '#fff7ed' : '#fff';
      const fw = isLabel ? '600' : 'normal';
      const align = isLabel ? 'center' : 'left';
      html += '<td style="border:1px solid #888;padding:6px 8px;background:' + bg
        + ';font-weight:' + fw + ';text-align:' + align
        + ';vertical-align:top;white-space:pre-wrap;">'
        + escapeHtml_(String(row[c])).replace(/\n/g, '<br>') + '</td>';
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  return html;
}

function escapeHtml_(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function httpGet_(url) {
  const resp = UrlFetchApp.fetch(url, {
    muteHttpExceptions: true,
    followRedirects: true,
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; MealMenuBot/1.0)',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'ko,en;q=0.8'
    }
  });
  const code = resp.getResponseCode();
  if (code < 200 || code >= 300) throw new Error('GET 응답 ' + code + ': ' + url);
  return resp.getContentText();
}

/* =========================================================
 *  트리거 관리
 * ========================================================= */

/** 매주 일요일 오전 8시(KST)에 sendWeeklyMealMenu 실행되도록 트리거 설치 */
function installWeeklyTrigger() {
  removeAllTriggers();
  ScriptApp.newTrigger('sendWeeklyMealMenu')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.SUNDAY)
    .atHour(8)
    .inTimezone(CONFIG.timezone)
    .create();
  Logger.log('일요일 오전 8시(KST) 트리거가 설치되었습니다.');
}

/** sendWeeklyMealMenu 핸들러에 연결된 모든 트리거 제거 */
function removeAllTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  let removed = 0;
  for (let i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'sendWeeklyMealMenu') {
      ScriptApp.deleteTrigger(triggers[i]);
      removed++;
    }
  }
  Logger.log('제거된 트리거: ' + removed);
}

/* =========================================================
 *  로컬 디버깅 헬퍼
 * ========================================================= */

/** 첨부 없이 사이트 분석 결과만 로그로 확인 */
function debugProbeSources() {
  for (const src of CONFIG.sources) {
    try {
      if (src.type === 'khu') {
        const html = httpGet_(src.url);
        const imgTag = html.match(/<img[^>]*\bclass="[^"]*\borg_image\b[^"]*"[^>]*>/i);
        Logger.log('[' + src.key + '] org_image: ' + (imgTag ? imgTag[0].substring(0, 200) : 'NOT FOUND'));
      } else if (src.type === 'hufs') {
        const pageHtml = httpGet_(src.url);
        const params = parseHufsFormParams_(pageHtml);
        Logger.log('[' + src.key + '] form params: ' + JSON.stringify(params));
      }
    } catch (e) {
      Logger.log('[' + src.key + '] 오류: ' + e.message);
    }
  }
}
