// ─── 成人/擦边内容过滤 ─────────────────────────────────────
//
// 聚合器会展开上百个直播源文件，其中难免混入成人频道。
// 黑名单只能按「源 URL」屏蔽整源，但同一源内也可能夹带成人频道，
// 因此在输出给客户端前，对直播组/频道名再做一次精细过滤。
//
// 设计要点（v2，2026-10-23 复检后修订）：
// 1. 两层判定：
//    - ADULT_ABSOLUTE（绝对信号）：成人厂牌/平台/番号等，正常内容不会出现，
//      命中即剔除，安全词不豁免 —— 修复「天美传媒…配对游戏」被组名里
//      的"游戏"误放行的问题；
//    - ADULT_STRONG（强信号）：行为词，命中且无安全词时剔除。
// 2. 安全词里去掉 动漫/游戏/二次元/电竞 —— 否则「Short」动漫游戏角色
//    分组里 50+ 个成人动漫会被组名整体豁免；电影/电视剧类安全词保留，
//    保护《什么叫做爱》《偷窥者》这类正常影片名。
// 3. 番号正则排除 CCTV/RTHK/NBA/ATP 等正常频道编号。
// 4. 同名且频道完全相同的直播组只保留第一个（上游会重复列出同一份源）。

const ADULT_ABSOLUTE: Array<string | RegExp> = [
  // 成人厂牌（含简繁/同音变体）
  '麻麻传媒', '麻豆传媒', '密桃传媒', '蜜桃传媒', '蜜室桃', '蜜桃影像',
  '天美传媒', '星辰传媒', '国产传媒', '爱豆传媒', '爱神传媒', '果冻传媒',
  '渡边传媒', '星空传媒', '精东影业', '几个传媒', 'SA国际传媒',
  // 成人平台
  'FC2', 'Brazzers', 'Pornhub', 'xvideos', 'xhamster', 'redtube',
  'spankbang', 'onlyfans', 'Jable', 'SupJav', 'MissAV', 'JavBus', 'JavDb', '超碰',
  // 流出 / 无码
  '無碼流出', '无码流出', '流出版', '无码片',
  // 知名 AV 女优
  '三上悠亚', '上原亚衣', '篠田ゆう',
  // 其它强标签
  'Hentai', 'R18', '18禁', '禁漫', '街头露出', '援交',
  // 独立成词的 SEX（不匹配 sexual/Essex 等英文单词内部）
  /(?:^|[^a-z])sex(?:$|[^a-z])/i,
  // JAV 番号（ABW-314 / SSIS-905…），排除正常电视台与赛事编号
  /\b(?!CCTV|CETV|ATV|BTV|GDTV|STV|TVB|HBO|BBC|CNN|ESPN|NBA|ATP|WTA|UFC|MTV|KBS|MBC|NHK|EPL|LPL|KPL|CBA|CSL|CGTN|FTV|ETTV|TTV|PTS|RTHK)[A-Z]{2,6}-\d{2,5}\b/,
];

const ADULT_STRONG: string[] = [
  // 明确成人行为（含繁体变体）
  '偷窥', '自慰', '做爱', '口交', '性爱', '裸聊', '裸播', '裸体', '全裸', '一丝不挂',
  '强姦', '强奸', '调教', '調教', '誘惑', '潮吹', '露出', '偷情', '情趣', '约炮', '一夜情',
  // 明确成人产业
  'AV女优', 'AV主播', 'AV资源', 'AV影片', '日AV', '无码流出', '无码视频', '有码流出',
  '日本AV', '步兵番号', '番号', '里番', '福利姬', '痴女', '嫩模', '素人',
  '无码资源', '有码资源', '麻豆视频', '麻豆电影',
  // 明确成人标签
  '三级片', '伦理片', '禁漫', 'Hentai',
  // 明确成人短语
  '小萝莉爱爱', '萝莉爱爱', '重口味爱好者', '媚宅', '涩涩', '色播', '色猫',
  '大尺度', '香艳', '艳遇', '情涩', '激情时刻', '性福', '春色满园',
  '春宵', '巨乳', '爆乳', '奶子', '骚货', '骚年', '干柴烈火',
  '女优', 'AV片', '色情片', '重口味', '小电影',
  // 成人传媒品牌 / 特定剧集前缀
  '会所偷拍', '酒店偷拍', '偷拍', '啪啪', '猛操', '狠操', '强上', '巨屌',
  '塞满', '囚禁', '无码', '無碼', '深喉', '小穴', '骚逼', '内射', '精液', '群P', '大屄', '淫水',
];

// 命中即放行（正常影视/综艺/体育/音乐等，避免误杀）。
// 注意：不含 动漫/游戏/二次元/电竞 —— 那是成人动漫最爱的伪装词。
const SAFE_OVERRIDE: string[] = [
  '速度与激情', '回家的诱惑', '干就完了', 'bravo', 'travel',
  '知识', '综艺', '科普', '纪实', '纪录片', '资讯', '体育', '赛事',
  '青春', '剧场', '电影', '电视剧', '连续剧',
  'BBC', 'CCTV', '卫视', '新闻', '演播厅', '挑战', '达人', '脱口秀',
  '音乐现场', '演唱会', 'MV', '旅游',
  '经济', '军事', '农业', '少儿', '戏曲', '购物', '农业农村',
  '骚火', '白嫖', '裸奔的蜗牛', '漫威', '粉丝福利', '茶杯狐', 'WebDav',
  '女优灵', // 1996 日本恐怖片《女優霊》，正常影片
];

// 整组剔除（直播组名级成人源）
const ADULT_GROUP = /成人|18\+|sex|porm|porn|fc2|麻豆|传媒|番号|伦理|三级|自拍|福利|媚|丝袜|诱惑|无码|有码|偷拍|约炮|裸|骚|pron|jable|missav|超碰|激情|艳|情趣|色情|av片/gi;

// 字符串模式在小写文本上匹配；正则在原文上匹配
// （番号正则区分大小写，只能跑原文，toLowerCase 后 [A-Z] 永远不命中）
function matchAny(low: string, orig: string, list: Array<string | RegExp>): boolean {
  for (const p of list) {
    if (typeof p === 'string') {
      if (low.includes(p.toLowerCase())) return true;
    } else if (p.test(orig)) {
      return true;
    }
  }
  return false;
}

function isAdultChannelText(text: string): boolean {
  const low = text.toLowerCase();
  if (matchAny(low, text, ADULT_ABSOLUTE)) return true;
  for (const s of SAFE_OVERRIDE) {
    if (low.includes(s.toLowerCase())) return false;
  }
  return matchAny(low, text, ADULT_STRONG);
}

interface LiveChannelLike {
  name?: string;
  urls?: string[];
  [k: string]: unknown;
}

interface LiveGroupLike {
  group?: string;
  channels?: LiveChannelLike[];
  [k: string]: unknown;
}

/**
 * 过滤直播组中的成人内容。
 * 返回新数组；原对象不被修改。
 */
export function filterAdultLives<T extends LiveGroupLike>(lives: T[] | undefined): T[] {
  if (!Array.isArray(lives) || lives.length === 0) return lives ?? [];

  const out: T[] = [];
  const seenGroups = new Set<string>();
  for (const g of lives) {
    const gname = String(g.group ?? '');
    if (gname && ADULT_GROUP.test(gname)) {
      ADULT_GROUP.lastIndex = 0;
      continue; // 整组丢弃
    }
    ADULT_GROUP.lastIndex = 0;

    const channels = g.channels;
    if (!Array.isArray(channels)) {
      out.push(g);
      continue;
    }
    const keep = channels.filter((c) => !isAdultChannelText(`${c.name ?? ''} ${gname}`));
    if (keep.length === 0) continue; // 组内全被过滤 → 整组丢弃

    // 同名且频道名完全相同的组只留第一个（上游重复列出的同一份直播）
    if (gname && channels.length > 0) {
      const sig = gname + '\u0000' + keep.map((c) => String(c.name ?? '')).join('\u0001');
      if (seenGroups.has(sig)) continue;
      seenGroups.add(sig);
    }

    if (keep.length === channels.length) {
      out.push(g);
    } else {
      out.push({ ...g, channels: keep });
    }
  }
  return out;
}

// ─── 点播站点过滤 ─────────────────────────────────────────
// 站点名 + api/ext 里出现绝对信号直接剔除（上游偶尔夹带成人资源站，
// 名字用 emoji 打擦边球，靠出口过滤兜底）
export function filterAdultSites<T extends { name?: string; api?: string; ext?: unknown }>(
  sites: T[] | undefined,
): T[] {
  if (!Array.isArray(sites) || sites.length === 0) return sites ?? [];
  return sites.filter((s) => {
    const name = String(s.name ?? '');
    const api = String(s.api ?? '');
    return !isAdultChannelText(`${name} ${api}`);
  });
}

// 对完整配置 JSON 应用直播+站点过滤，带单项缓存。
// 聚合一天只跑一次，缓存的配置串不变时直接复用上次结果，
// 避免 15 万频道 × 请求级别的重复扫描。
let filterCache: { input: string; output: string } | null = null;

export function applyLiveFilterToConfigJson(raw: string): string {
  if (filterCache && filterCache.input === raw) return filterCache.output;
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed.sites)) {
      parsed.sites = filterAdultSites(parsed.sites);
    }
    if (Array.isArray(parsed.lives)) {
      parsed.lives = filterAdultLives(parsed.lives);
    }
    const out = JSON.stringify(parsed);
    filterCache = { input: raw, output: out };
    return out;
  } catch { /* 解析失败保持原样 */ }
  return raw;
}
