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

/** 메인: KHU는 페이지 이미지 첨부, HUFS는 Rendex로 HTML→PNG 변환 첨부 */
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
        const blob = fetchHufsPngViaRendex_(src);
        attachments.push(blob);
        lines.push('상태: 첨부 완료 (' + blob.getName() + ')');
        htmlSections.push('<p>상태: 첨부 완료 (' + escapeHtml_(blob.getName()) + ')</p>');
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
  try {
    const folder = getCacheFolder_();
    const fileName = cacheFileNameForKhu_(src);
    const it = folder.getFilesByName(fileName);
    if (!it.hasNext()) return null;
    const f = it.next();
    Logger.log('[' + src.key + '] 캐시 사용 (Drive: ' + fileName + ')');
    return f.getBlob().setName(fileName);
  } catch (e) {
    Logger.log('[' + src.key + '] 캐시 조회 일시 오류(skip→fetch): ' + e.message);
    return null;
  }
}

function saveKhuBlobToCache_(src, blob) {
  try {
    const folder = getCacheFolder_();
    const fileName = cacheFileNameForKhu_(src);
    if (folder.getFilesByName(fileName).hasNext()) return;
    folder.createFile(blob.copyBlob().setName(fileName));
    Logger.log('[' + src.key + '] 캐시 저장: ' + fileName);
  } catch (e) {
    Logger.log('[' + src.key + '] 캐시 저장 일시 오류(무시): ' + e.message);
  }
}

function mostRecentKhuCacheBlob_(src) {
  try {
    const folder = getCacheFolder_();
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
  } catch (e) {
    Logger.log('[' + src.key + '] stale 캐시 조회 일시 오류: ' + e.message);
    return null;
  }
}

/* =========================================================
 *  HUFS — 주간 메뉴 HTML 테이블 → 메일 본문 inline HTML
 * ========================================================= */

/**
 * HUFS 주간 메뉴를 Rendex API로 PNG 변환하여 첨부용 blob 반환.
 * - 캐시 키: KHU와 동일 패턴 (src.key + '_' + ISO주 + '.png')
 * - 라이브 fetch 실패 시 stale(전주 등) 캐시 fallback
 */
function fetchHufsPngViaRendex_(src) {
  const cached = cachedKhuBlob_(src);
  if (cached) return cached;

  try {
    // 1) HUFS 페이지 + AJAX fetch + parse → 2D grid
    const pageHtml = httpGet_(src.url);
    const params = parseHufsFormParams_(pageHtml);
    if (!params.year || !params.month || !params.weekFirst || !params.weekLast) {
      throw new Error('HUFS 폼 파라미터 추출 실패: ' + JSON.stringify(params));
    }
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          + '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': src.url
      }
    }).getContentText();
    const grid = parseHufsMenuTable_(menuHtml);
    if (!grid || grid.length < 2) throw new Error('HUFS 메뉴 테이블 파싱 결과가 비어 있습니다');

    // 2) 표 + 헤더 wrapper HTML
    const wrappedHtml = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
      + 'body{font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif;'
      + 'margin:24px;background:#fff;color:#1f2937;}'
      + 'h2{margin:0 0 16px 0;font-size:20px;}'
      + '</style></head><body>'
      + '<h2>' + escapeHtml_(src.name) + '</h2>'
      + renderGridAsHtml_(grid)
      + '</body></html>';

    // 3) Rendex API로 PNG 변환
    const apiKey = PropertiesService.getScriptProperties().getProperty('RENDEX_API_KEY');
    if (!apiKey) throw new Error('RENDEX_API_KEY 미설정 (스크립트 속성에 등록 필요)');
    const resp = UrlFetchApp.fetch('https://api.rendex.dev/v1/screenshot', {
      method: 'post',
      headers: {
        'Authorization': 'Bearer ' + apiKey,
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify({
        html: wrappedHtml,
        format: 'png',
        width: 1400,
        height: 900
      }),
      muteHttpExceptions: true
    });
    const code = resp.getResponseCode();
    const ct = (resp.getHeaders()['Content-Type'] || resp.getHeaders()['content-type'] || '').toString();
    if (code !== 200 || ct.indexOf('image/') !== 0) {
      throw new Error('Rendex 응답 실패 — code=' + code + ', CT=' + ct
        + ', body=' + resp.getContentText().substring(0, 300));
    }
    const blob = resp.getBlob().setName(src.key + '.png').setContentType('image/png');

    // 4) 캐시 저장 (KHU와 동일 헬퍼 재사용 — 파일명 = src.key + '_' + ISO주 + '.png')
    try { saveKhuBlobToCache_(src, blob); }
    catch (e) { Logger.log('[' + src.key + '] 캐시 저장 실패(무시): ' + e.message); }
    return blob;
  } catch (e) {
    // 라이브 fetch 실패 시 stale 캐시 fallback
    const stale = mostRecentKhuCacheBlob_(src);
    if (stale) {
      Logger.log('[' + src.key + '] 라이브 fetch 실패 → stale 캐시 사용: ' + e.message);
      return stale;
    }
    throw e;
  }
}

function fetchHufsMenuHtml_(src) {
  // KHU와 같은 ISO 주 단위 Drive 캐시 (HUFS 사이트도 quota 걸리는 케이스 방지)
  const cached = cachedHufsHtml_(src);
  if (cached) return cached;

  try {
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          + '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': src.url
      }
    }).getContentText();

    // 3) 메뉴 테이블 → 2D 배열
    const grid = parseHufsMenuTable_(menuHtml);
    if (!grid || grid.length < 2) throw new Error('HUFS 메뉴 테이블 파싱 결과가 비어 있습니다');

    // 4) 2D 배열 → 메일 본문 inline용 HTML 표 + 캐시 저장
    const html = renderGridAsHtml_(grid);
    try { saveHufsHtmlToCache_(src, html); }
    catch (e) { Logger.log('[' + src.key + '] 캐시 저장 실패(무시): ' + e.message); }
    return html;
  } catch (e) {
    // 라이브 fetch 실패 시 가장 최근 stale 캐시(전주 등)라도 사용
    const stale = mostRecentHufsHtmlCache_(src);
    if (stale) {
      Logger.log('[' + src.key + '] 라이브 fetch 실패 → stale 캐시 사용: ' + e.message);
      return stale;
    }
    throw e;
  }
}

function cachedHufsHtml_(src) {
  try {
    const folder = getCacheFolder_();
    const week = isoWeekKey_(new Date(), CONFIG.timezone);
    const fileName = src.key + '_' + week + '.html';
    const it = folder.getFilesByName(fileName);
    if (!it.hasNext()) return null;
    const f = it.next();
    Logger.log('[' + src.key + '] 캐시 사용 (Drive: ' + fileName + ')');
    return f.getBlob().getDataAsString('UTF-8');
  } catch (e) {
    Logger.log('[' + src.key + '] 캐시 조회 일시 오류(skip→fetch): ' + e.message);
    return null;
  }
}

function saveHufsHtmlToCache_(src, html) {
  try {
    const folder = getCacheFolder_();
    const week = isoWeekKey_(new Date(), CONFIG.timezone);
    const fileName = src.key + '_' + week + '.html';
    if (folder.getFilesByName(fileName).hasNext()) return;
    folder.createFile(fileName, html, MimeType.HTML);
    Logger.log('[' + src.key + '] 캐시 저장: ' + fileName);
  } catch (e) {
    Logger.log('[' + src.key + '] 캐시 저장 일시 오류(무시): ' + e.message);
  }
}

function mostRecentHufsHtmlCache_(src) {
  try {
    const folder = getCacheFolder_();
    const it = folder.getFiles();
    let best = null;
    let bestTime = 0;
    while (it.hasNext()) {
      const f = it.next();
      const name = f.getName();
      if (name.indexOf(src.key + '_') !== 0) continue;
      if (name.indexOf('.html') === -1) continue;
      const t = f.getLastUpdated().getTime();
      if (t > bestTime) { bestTime = t; best = f; }
    }
    return best ? best.getBlob().getDataAsString('UTF-8') : null;
  } catch (e) {
    Logger.log('[' + src.key + '] stale 캐시 조회 일시 오류: ' + e.message);
    return null;
  }
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

/* =========================================================
 *  EXPERIMENTAL — Slides → PNG PoC (Phase B-2)
 *  main의 sendWeeklyMealMenu 흐름은 손대지 않음. 함수 단독 실행으로만 검증.
 *  성공 시 main의 HUFS 분기를 PNG 첨부로 swap한다.
 * ========================================================= */

function debugTrySlidesPng() {
  const ps = SlidesApp.create('__exp_slides_' + Date.now());
  const psId = ps.getId();
  const slide = ps.getSlides()[0];

  // HUFS 메뉴 표 흉내
  const grid = [
    ['요일', '월(28)', '화(29)', '수(30)', '목(1)', '금(2)'],
    ['조식', '쌀밥, 미역국', '잡곡밥, 김치찌개', '비빔밥', '카레라이스', '오므라이스'],
    ['중식', '돈까스', '비빔국수', '제육볶음', '갈비탕', '닭갈비'],
    ['석식', '치킨', '햄버그스테이크', '연어구이', '불고기', '파스타']
  ];
  const tbl = slide.insertTable(grid.length, grid[0].length);
  for (let r = 0; r < grid.length; r++) {
    for (let c = 0; c < grid[0].length; c++) {
      tbl.getCell(r, c).getText().setText(String(grid[r][c]));
    }
  }
  Utilities.sleep(2000);

  let blob = null;
  let report = [];

  // 시도1: Drive REST v3 export?mimeType=image/png (Slides는 PNG export 공식 지원)
  try {
    const url = 'https://www.googleapis.com/drive/v3/files/' + psId
      + '/export?mimeType=image%2Fpng';
    const resp = UrlFetchApp.fetch(url, {
      headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
      muteHttpExceptions: true
    });
    const code = resp.getResponseCode();
    const ct = (resp.getHeaders()['Content-Type'] || '').toString();
    report.push('시도1 Drive REST PNG: code=' + code + ', CT=' + ct);
    if (code === 200 && ct.indexOf('image/') === 0) {
      blob = resp.getBlob().setName('slides_poc.png').setContentType('image/png');
      report.push('  → 성공 ' + blob.getBytes().length + ' bytes');
    } else {
      report.push('  → 실패 body=' + resp.getContentText().substring(0, 200));
    }
  } catch (e) {
    report.push('시도1 예외: ' + e.message);
  }

  // 시도2: Slides API thumbnail endpoint (시도1 실패 시)
  if (!blob) {
    try {
      const slideId = slide.getObjectId();
      const url = 'https://slides.googleapis.com/v1/presentations/' + psId
        + '/pages/' + slideId
        + '/thumbnail?thumbnailProperties.thumbnailSize=LARGE&thumbnailProperties.mimeType=PNG';
      const resp = UrlFetchApp.fetch(url, {
        headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
        muteHttpExceptions: true
      });
      const code = resp.getResponseCode();
      report.push('시도2 Slides thumbnail API: code=' + code);
      if (code === 200) {
        const json = JSON.parse(resp.getContentText());
        report.push('  contentUrl=' + (json.contentUrl || '').substring(0, 80) + '...');
        if (json.contentUrl) {
          const img = UrlFetchApp.fetch(json.contentUrl, { muteHttpExceptions: true });
          const ic = img.getResponseCode();
          report.push('  contentUrl fetch: code=' + ic);
          if (ic === 200) {
            blob = img.getBlob().setName('slides_poc.png').setContentType('image/png');
            report.push('  → 성공 ' + blob.getBytes().length + ' bytes');
          }
        }
      } else {
        report.push('  → 실패 body=' + resp.getContentText().substring(0, 200));
      }
    } catch (e) {
      report.push('시도2 예외: ' + e.message);
    }
  }

  Logger.log('[B-2 PoC]\n' + report.join('\n'));

  GmailApp.sendEmail(CONFIG.recipient,
    blob ? '[PoC] Slides → PNG 성공' : '[PoC] Slides → PNG 실패',
    report.join('\n'),
    { name: CONFIG.senderName, attachments: blob ? [blob] : [] });

  try { DriveApp.getFileById(psId).setTrashed(true); }
  catch (e) { Logger.log('Slides 정리 실패: ' + e.message); }
}

/* =========================================================
 *  EXPERIMENTAL — Rendex (외부 HTML→PNG API) PoC (Phase B-3)
 *  https://api.rendex.dev/v1/screenshot
 *  무료 500/월, API key는 Script Properties의 'RENDEX_API_KEY'에 저장
 * ========================================================= */

function debugTryRendex() {
  const apiKey = PropertiesService.getScriptProperties().getProperty('RENDEX_API_KEY');
  if (!apiKey) {
    const msg = 'RENDEX_API_KEY 미설정 — Apps Script 편집기 → ⚙️ 프로젝트 설정 → 스크립트 속성에서 추가';
    Logger.log(msg);
    GmailApp.sendEmail(CONFIG.recipient, '[PoC] Rendex 키 미설정', msg,
      { name: CONFIG.senderName });
    return;
  }

  const testHtml = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
    + 'body{font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif;margin:24px;}'
    + 'h2{margin:0 0 12px 0;}'
    + 'table{border-collapse:collapse;width:100%;font-size:14px;}'
    + 'th,td{border:1px solid #888;padding:8px;text-align:left;vertical-align:top;}'
    + 'th{background:#fde68a;text-align:center;}'
    + 'td:first-child{background:#fff7ed;font-weight:600;text-align:center;}'
    + '</style></head><body>'
    + '<h2>한국외대 인문관 식당 (PoC)</h2>'
    + '<table><thead><tr><th>요일/메뉴</th><th>월</th><th>화</th><th>수</th></tr></thead>'
    + '<tbody>'
    + '<tr><td>조식</td><td>쌀밥, 미역국</td><td>잡곡밥, 김치찌개</td><td>비빔밥</td></tr>'
    + '<tr><td>중식</td><td>돈까스</td><td>비빔국수</td><td>제육볶음</td></tr>'
    + '<tr><td>석식</td><td>치킨</td><td>햄버그</td><td>연어구이</td></tr>'
    + '</tbody></table></body></html>';

  const resp = UrlFetchApp.fetch('https://api.rendex.dev/v1/screenshot', {
    method: 'post',
    headers: {
      'Authorization': 'Bearer ' + apiKey,
      'Content-Type': 'application/json'
    },
    payload: JSON.stringify({
      html: testHtml,
      format: 'png',
      width: 1200,
      height: 800
    }),
    muteHttpExceptions: true
  });
  const code = resp.getResponseCode();
  const ct = (resp.getHeaders()['Content-Type'] || resp.getHeaders()['content-type'] || '').toString();
  Logger.log('[Rendex PoC] code=' + code + ', CT=' + ct);

  if (code === 200 && ct.indexOf('image/') === 0) {
    const blob = resp.getBlob().setName('rendex_poc.png').setContentType('image/png');
    Logger.log('[Rendex PoC] 성공 ' + blob.getBytes().length + ' bytes');
    GmailApp.sendEmail(CONFIG.recipient, '[PoC] Rendex → PNG 성공',
      'Rendex API 동작 확인. 첨부 확인.\n크기=' + blob.getBytes().length + ' bytes',
      { name: CONFIG.senderName, attachments: [blob] });
  } else {
    const body = resp.getContentText().substring(0, 500);
    Logger.log('[Rendex PoC] 실패 body=' + body);
    GmailApp.sendEmail(CONFIG.recipient, '[PoC] Rendex → PNG 실패',
      'code=' + code + '\nContent-Type=' + ct + '\nbody=' + body,
      { name: CONFIG.senderName });
  }
}
