/**
 * 规则字段提取（前端镜像）：只抽取能在原文中定位的字段。
 * 与 backend/app/services/extract.py 是同一套规则，修改时两份需同步。
 * api 模式下由后端 POST /api/extract 返回同样结构，模型接入后只替换后端实现。
 */

export const FIELD_LABELS = {
  merchant: '商家名称',
  amount: '交易金额',
  product: '商品/服务',
  goal: '当前诉求',
  platform: '交易平台',
  tradeTime: '交易时间',
  creditCode: '信用代码',
}

const REQUIRED = [
  ['merchant', '商家名称'],
  ['amount', '交易金额'],
  ['product', '商品/服务'],
  ['tradeTime', '交易时间'],
]

const PLATFORMS = ['苏宁易购', '拼多多', '唯品会', '小红书', '淘宝', '天猫', '京东', '抖音', '快手', '美团', '饿了么', '闲鱼', '苏宁', '线下门店', '实体店', '超市', '商场']

const GOALS = [
  [['退货退款', '退款', '退钱', '退费', '返还', '不退', '不给退', '拒绝退'], '退货退款'],
  [['换货', '更换', '换个'], '换货'],
  [['维修', '修理', '修好'], '维修'],
  [['赔偿', '赔付', '补偿'], '赔偿'],
  [['补发', '重发'], '补发'],
]

// 后缀越长越靠前，避免「旗舰店」被「店」截断。
const MERCHANT_SUFFIXES = ['官方旗舰店', '旗舰店', '专卖店', '专营店', '官方店', '网店', '商店', '店铺', '公司', '健身房', '超市', '餐厅', '饭店', '餐馆', '酒店', '宾馆', '商城', '商场', '门店', '药店', '药房', '影楼', '旅行社', '维修店', '便利店', '经营部', '批发部', '店']
const MERCHANT_STOP = new Set(['商家', '店家', '客服', '平台', '卖家', '对方', '公司', '门店', '实体店', '线下门店'])
const MERCHANT_VERB_PREFIX = ['联系', '咨询', '询问', '投诉', '找到', '跟', '和', '向', '这家', '那家', '该']
const MERCHANT_CALL_RE = /(?:商家|卖家|店铺|店名|老板|对方)(?:名字|名称|叫啥|叫什么)?\s*(?:叫|是|为)\s*[「“"']?([\u4e00-\u9fa5A-Za-z0-9]{2,20})[」”"']?/

const PRODUCT_VERBS = ['购买了', '购买', '买了', '买', '入手了', '入手', '下单了', '下单', '订购了', '订购', '点了', '订了', '叫了']
const PRODUCT_NOISE = ['右侧', '左侧', '这边', '那边', '收到', '发现', '结果', '但是', '但', '可是', '却', '一直', '现在', '坏了', '有问题', '无法', '不能', '没有声音', '无声音', '没声音', '过期', '变质', '发霉', '破损', '漏液']

const AMOUNT_RE = /(?:¥|￥)\s*(\d[\d,]*(?:\.\d{1,2})?)|(\d[\d,]*(?:\.\d{1,2})?)\s*(?:元|块钱|块)/g
// 口语尾数：399块9 / 89块9毛；后面紧跟「月/日/年/号」时不当作金额小数。
const AMOUNT_FRACTION_RE = /^\s*([0-9])\s*(?:毛|角)?(?![0-9月日年号])/
const PRODUCT_AMOUNT_RE = /(?:¥|￥)|(\d[\d,]*(?:\.\d{1,2})?)\s*(?:元|块|毛)/
const FULL_DATE_RE = /(\d{4})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*[日号]?/
const SHORT_DATE_RE = /(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]/
const FESTIVALS = [['双十一', [11, 11]], ['双11', [11, 11]]]
const CREDIT_RE = /(?<![0-9A-Z])([0-9A-HJ-NPQRTUWXY]{18})(?![0-9A-Z])/

const pad = value => String(value).padStart(2, '0')
const iso = date => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`

function entry(field, value, snippet, start, end) {
  return { field, value, snippet, start, end }
}

function findAmount(text) {
  for (const match of text.matchAll(AMOUNT_RE)) {
    const raw = (match[1] || match[2]).replace(/,/g, '')
    let value = Number(raw)
    let end = match.index + match[0].length
    const fraction = text.slice(end, end + 4).match(AMOUNT_FRACTION_RE)
    if (fraction && !raw.includes('.')) {
      value = Math.round((value + Number(fraction[1]) / 10) * 10) / 10
      end += fraction[0].length
    }
    if (value > 0 && value <= 100000000) {
      return { value, snippet: text.slice(match.index, end).trim(), start: match.index, end }
    }
  }
  return null
}

function findPlatform(text) {
  const hits = PLATFORMS.map(name => ({ index: text.indexOf(name), name })).filter(hit => hit.index >= 0)
  if (!hits.length) return null
  hits.sort((a, b) => a.index - b.index || b.name.length - a.name.length)
  const { index, name } = hits[0]
  return { value: name, snippet: name, start: index, end: index + name.length }
}

function findProduct(text) {
  for (const verb of PRODUCT_VERBS) {
    const index = text.indexOf(verb)
    if (index < 0) continue
    const start = index + verb.length
    let head = text.slice(start, start + 40).replace(/^[，,。；、 了的]+/, '').split(/[，,。；;！!？?\n]/)[0]
    head = head.replace(/^[了]?(?:一|两|三|几|半)?[个台部双件张只瓶盒套份]?/, '')
    // 商品名后面常跟金额（「无线耳机399元」），先截掉，避免金额混进商品名。
    const amountHit = head.match(PRODUCT_AMOUNT_RE)
    if (amountHit) {
      const at = amountHit.index
      head = at === 0 ? head.slice(amountHit[0].length).replace(/^的/, '') : head.slice(0, at)
    }
    for (const noise of PRODUCT_NOISE) {
      if (head.includes(noise)) head = head.split(noise)[0]
    }
    const value = head.replace(/^的/, '').replace(/[，,。；、的]+$/, '').trim()
    if (!value || value.length > 20) continue
    const position = text.indexOf(value, start)
    const startAt = position < 0 ? start : position
    return { value, snippet: value, start: startAt, end: startAt + value.length }
  }
  return null
}

function findGoal(text) {
  const hits = []
  GOALS.forEach(([keywords, goal]) => {
    const found = keywords.map(keyword => ({ index: text.indexOf(keyword), keyword })).filter(item => item.index >= 0)
    if (found.length) {
      found.sort((a, b) => a.index - b.index)
      hits.push({ index: found[0].index, keyword: found[0].keyword, goal })
    }
  })
  if (!hits.length) return null
  hits.sort((a, b) => a.index - b.index)
  const value = hits.map(hit => hit.goal).join('、')
  const { index, keyword } = hits[0]
  return { value, snippet: keyword, start: index, end: index + keyword.length }
}

function findMerchant(text) {
  const call = text.match(MERCHANT_CALL_RE)
  if (call) {
    const name = call[1]
    const start = call.index + call[0].lastIndexOf(name)
    if (name.length >= 3 && !MERCHANT_STOP.has(name) && !/^[我你他她它]/.test(name)) {
      return { value: name, snippet: name, start, end: start + name.length }
    }
  }
  const pattern = new RegExp(`([\\u4e00-\\u9fa5A-Za-z0-9]{2,20}(?:${MERCHANT_SUFFIXES.join('|')}))`, 'g')
  for (const match of text.matchAll(pattern)) {
    let name = match[1]
    name = name.replace(/^(?:这家|那家|该|这个|那个|一家|在|于|从)/, '')
    if (name.length < 3 || MERCHANT_STOP.has(name)) continue
    if (MERCHANT_VERB_PREFIX.some(prefix => name.startsWith(prefix))) continue
    const offset = Math.max(match[1].indexOf(name), 0)
    const start = match.index + offset
    return { value: name, snippet: name, start, end: start + name.length }
  }
  return null
}

function findTradeTime(text, today) {
  const full = text.match(FULL_DATE_RE)
  if (full) {
    const date = new Date(Number(full[1]), Number(full[2]) - 1, Number(full[3]))
    if (date.getFullYear() === Number(full[1]) && date.getMonth() === Number(full[2]) - 1 && date.getDate() === Number(full[3]) && date <= today) {
      return { value: iso(date), snippet: full[0], start: full.index, end: full.index + full[0].length }
    }
  }
  for (const [word, [month, day]] of FESTIVALS) {
    const index = text.indexOf(word)
    if (index < 0) continue
    for (const year of [today.getFullYear(), today.getFullYear() - 1]) {
      const date = new Date(year, month - 1, day)
      if (date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day && date <= today) {
        return { value: iso(date), snippet: word, start: index, end: index + word.length }
      }
    }
  }
  const short = text.match(SHORT_DATE_RE)
  if (short) {
    const month = Number(short[1])
    const day = Number(short[2])
    for (const year of [today.getFullYear(), today.getFullYear() - 1]) {
      const date = new Date(year, month - 1, day)
      if (date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day && date <= today) {
        return { value: iso(date), snippet: short[0], start: short.index, end: short.index + short[0].length }
      }
    }
  }
  const relative = [['大前天', -3], ['前天', -2], ['昨天', -1], ['今天', 0], ['上周', -7], ['上个月', -30]]
  for (const [word, offset] of relative) {
    const index = text.indexOf(word)
    if (index >= 0) {
      const date = new Date(today)
      date.setDate(date.getDate() + offset)
      return { value: iso(date), snippet: word, start: index, end: index + word.length }
    }
  }
  return null
}

export function extractFields(rawText, today = new Date()) {
  const text = rawText || ''
  const fields = {}
  const evidence = []
  const add = result => {
    if (!result) return
    fields[result.field] = result.value
    evidence.push(entry(result.field, result.value, result.snippet, result.start, result.end))
  }

  const amount = findAmount(text)
  if (amount) add({ field: 'amount', ...amount })
  const platform = findPlatform(text)
  if (platform) add({ field: 'platform', ...platform })
  const product = findProduct(text)
  if (product) add({ field: 'product', ...product })
  const goal = findGoal(text)
  if (goal) add({ field: 'goal', ...goal })
  const merchant = findMerchant(text)
  if (merchant) add({ field: 'merchant', ...merchant })
  const tradeTime = findTradeTime(text, today)
  if (tradeTime) add({ field: 'tradeTime', ...tradeTime })

  const credit = text.match(CREDIT_RE)
  if (credit) {
    fields.creditCode = credit[1]
    evidence.push(entry('creditCode', credit[1], credit[0], credit.index, credit.index + credit[0].length))
  }

  const missing = REQUIRED.filter(([field]) => !(field in fields)).map(([field, label]) => ({ field, label }))
  return { fields, evidence, missing }
}
