/**
 * 各领域特殊页（404 / 500 / 加载）文案与图形母题。
 * 配色走 themes.css 的 --portal-*，此处只定「领域个性」。
 */
import { getDelivered, getFlavor, getDomainLabel, schemaLabels } from './domainSchema.js'

const FLAVORS = {
  'library': {
    motif: 'book',
    notFound: {
      title: '这本书不在架上',
      lead: '你要找的页面可能已下架，或索书号写错了。',
      hint: '回目录重新检索，或从首页继续浏览藏书。',
    },
    serverError: {
      title: '阅览室临时闭馆',
      lead: '服务端出了点状况，书页暂时翻不开。',
      hint: '稍后再试；若持续出现，请联系管理员。',
    },
    loading: {
      title: '正在取书…',
      lead: '索书号核对中，马上送到你手上。',
    },
  },
  'equipment': {
    motif: 'gear',
    notFound: {
      title: '设备不在库',
      lead: '该页面或设备条目未找到，可能已调拨。',
      hint: '返回设备列表，重新筛选可用器材。',
    },
    serverError: {
      title: '库房系统离线',
      lead: '借用服务暂时不可用，请稍候。',
      hint: '可先核对设备编号，稍后再提交申请。',
    },
    loading: {
      title: '正在核对可用数量…',
      lead: '设备状态同步中。',
    },
  },
  'asset': {
    motif: 'box',
    notFound: {
      title: '物资未登记',
      lead: '找不到对应页面或台账条目。',
      hint: '回物资目录核对编号后再试。',
    },
    serverError: {
      title: '台账服务异常',
      lead: '物资系统暂时响应失败。',
      hint: '请稍后重试浏览或提交申领。',
    },
    loading: {
      title: '台账加载中…',
      lead: '正在汇总台账与申领记录。',
    },
  },
  'crm': {
    motif: 'users',
    notFound: {
      title: '客户未找到',
      lead: '页面无效，或客户/跟进单不存在。',
      hint: '回客户列表重新选择。',
    },
    serverError: {
      title: '跟进服务异常',
      lead: '客户系统暂时连不上。',
      hint: '请稍后重试提交或查询跟进。',
    },
    loading: {
      title: '客户加载中…',
      lead: '正在同步资料与跟进记录。',
    },
  },
  'event': {
    motif: 'clipboard',
    notFound: {
      title: '事件未找到',
      lead: '页面无效，或事件/上报单不存在。',
      hint: '回事件列表重新选择。',
    },
    serverError: {
      title: '上报服务异常',
      lead: '事件系统暂时连不上。',
      hint: '请稍后重试提交或查询上报。',
    },
    loading: {
      title: '事件加载中…',
      lead: '正在同步档案与上报记录。',
    },
  },
  'shop': {
    motif: 'cart',
    notFound: {
      title: '商品已下架',
      lead: '该页面或商品链接失效了。',
      hint: '回商城首页看看今日上新。',
    },
    serverError: {
      title: '收银台繁忙',
      lead: '交易服务暂时不可用。',
      hint: '购物车内容仍在，请稍后再结算。',
    },
    loading: {
      title: '正在备货…',
      lead: '商品信息加载中。',
    },
  },
  'dorm': {
    motif: 'bed',
    notFound: {
      title: '宿舍楼层走错了',
      lead: '页面不存在，或报修单号无效。',
      hint: '回我的报修查看进行中的工单。',
    },
    serverError: {
      title: '宿管值班室离线',
      lead: '报修服务暂时连不上。',
      hint: '紧急情况可先联系楼栋管理员。',
    },
    loading: {
      title: '工单派送中…',
      lead: '正在同步宿舍报修进度。',
    },
  },
  'property': {
    motif: 'wrench',
    notFound: {
      title: '工单未找到',
      lead: '该报修页面或单号不存在。',
      hint: '从报修列表重新选择工单。',
    },
    serverError: {
      title: '物业调度中断',
      lead: '受理服务暂时异常。',
      hint: '请稍后再次提交或查询进度。',
    },
    loading: {
      title: '师傅派单中…',
      lead: '正在匹配维修资源。',
    },
  },
  'ithelp': {
    motif: 'chip',
    notFound: {
      title: '节点未响应',
      lead: '页面路径无效，或工单号不存在。',
      hint: '回 IT 报修台重新检索。',
    },
    serverError: {
      title: '机房告警',
      lead: '后端服务返回了错误。',
      hint: '可先自查网络与账号，稍后再试。',
    },
    loading: {
      title: '诊断进行中…',
      lead: '正在拉取运维工单状态。',
    },
  },
  'activity': {
    motif: 'calendar',
    notFound: {
      title: '活动已结束或不存在',
      lead: '报名页或活动链接失效了。',
      hint: '看看还有哪些可报名的活动。',
    },
    serverError: {
      title: '报名通道拥堵',
      lead: '活动服务暂时不可用。',
      hint: '请稍后再试，避免重复提交。',
    },
    loading: {
      title: '名额确认中…',
      lead: '正在同步活动报名信息。',
    },
  },
  'lostfound': {
    motif: 'pin',
    notFound: {
      title: '启事已撤下',
      lead: '找不到该招领/寻物页面。',
      hint: '回失物招领榜重新浏览。',
    },
    serverError: {
      title: '公示栏暂时关闭',
      lead: '失物服务异常，请稍候。',
      hint: '登记内容稍后可再提交。',
    },
    loading: {
      title: '正在核对线索…',
      lead: '失物信息加载中。',
    },
  },
  'course': {
    motif: 'board',
    notFound: {
      title: '课程不在课表',
      lead: '选课页面或课程编号无效。',
      hint: '返回选课中心重新检索。',
    },
    serverError: {
      title: '教务系统繁忙',
      lead: '选课服务暂时不可用。',
      hint: '高峰期请错峰再试。',
    },
    loading: {
      title: '课表刷新中…',
      lead: '正在同步可选课程。',
    },
  },
  'food': {
    motif: 'bowl',
    notFound: {
      title: '菜品售罄下架',
      lead: '该点餐页面不存在了。',
      hint: '回菜单看看今日供应。',
    },
    serverError: {
      title: '后厨出餐延误',
      lead: '点餐服务暂时异常。',
      hint: '订单可稍后重试提交。',
    },
    loading: {
      title: '厨灶预热中…',
      lead: '菜单与档口信息加载中。',
    },
  },
  'hospital': {
    motif: 'cross',
    notFound: {
      title: '号源或页面不存在',
      lead: '挂号/就诊链接无效。',
      hint: '回预约入口重新选择科室。',
    },
    serverError: {
      title: '分诊台暂时离线',
      lead: '医疗服务接口异常。',
      hint: '急诊请线下就医；其余稍后再试。',
    },
    loading: {
      title: '排队叫号中…',
      lead: '正在同步预约与号源。',
    },
  },
  'parking': {
    motif: 'car',
    notFound: {
      title: '车位号无效',
      lead: '找不到该页面或车位记录。',
      hint: '回车位图重新选择空位。',
    },
    serverError: {
      title: '道闸系统异常',
      lead: '停车服务暂时不可用。',
      hint: '请稍后重试预约或出场。',
    },
    loading: {
      title: '车位扫描中…',
      lead: '正在更新空余车位。',
    },
  },
  'meeting': {
    motif: 'door',
    notFound: {
      title: '场地未开放',
      lead: '预约页或场地编号不存在。',
      hint: '从场地列表重新挑选时段。',
    },
    serverError: {
      title: '预约服务中断',
      lead: '场地预约暂时不可用。',
      hint: '请稍后再锁定时段。',
    },
    loading: {
      title: '场地准备中…',
      lead: '正在核对占用与空闲时段。',
    },
  },
  'salon': {
    motif: 'scissors',
    notFound: {
      title: '服务项目已调整',
      lead: '预约页面失效或不存在。',
      hint: '回服务列表重新选择。',
    },
    serverError: {
      title: '前台系统繁忙',
      lead: '预约服务暂时异常。',
      hint: '请稍后再锁定档期。',
    },
    loading: {
      title: '档期确认中…',
      lead: '正在加载可预约时段。',
    },
  },
  'hotel': {
    motif: 'key',
    notFound: {
      title: '房型已满或不存在',
      lead: '客房页面链接无效。',
      hint: '回房型列表重新挑选。',
    },
    serverError: {
      title: '前台登记暂停',
      lead: '客房服务暂时不可用。',
      hint: '请稍后再办理入住或入住。',
    },
    loading: {
      title: '客房整理中…',
      lead: '正在同步房态。',
    },
  },
  'media': {
    motif: 'film',
    notFound: {
      title: '片源不在片单',
      lead: '该影视页面已下架或链接错误。',
      hint: '回片库继续挑选想看的内容。',
    },
    serverError: {
      title: '放映中断',
      lead: '媒资服务暂时不可用。',
      hint: '收藏夹仍在，请稍后再打开。',
    },
    loading: {
      title: '缓冲中…',
      lead: '片单与封面加载中。',
    },
  },
  'music': {
    motif: 'note',
    notFound: {
      title: '曲目已下架',
      lead: '找不到该歌曲或页面。',
      hint: '回曲库继续挑歌。',
    },
    serverError: {
      title: '播放器失联',
      lead: '音乐服务暂时异常。',
      hint: '稍后再试，歌单不会丢失。',
    },
    loading: {
      title: '调音中…',
      lead: '曲库信息加载中。',
    },
  },
  'forum': {
    motif: 'board',
    notFound: {
      title: '帖子已撤下',
      lead: '该帖不存在或已被删除。',
      hint: '回板块继续浏览其他话题。',
    },
    serverError: {
      title: '论坛暂时拥挤',
      lead: '社区服务暂时不可用。',
      hint: '稍后再试，已发回复不会丢。',
    },
    loading: {
      title: '刷新中…',
      lead: '正在同步板块与楼层。',
    },
  },
  'blog': {
    motif: 'book',
    notFound: {
      title: '文章已下架',
      lead: '找不到该博文或链接失效。',
      hint: '回首页继续阅读其他文章。',
    },
    serverError: {
      title: '站点维护中',
      lead: '博客服务暂时异常。',
      hint: '稍后再打开，收藏夹仍在。',
    },
    loading: {
      title: '排版中…',
      lead: '文章与封面加载中。',
    },
  },
  'generic': {
    motif: 'grid',
    notFound: {
      title: '页面不存在',
      lead: '地址可能写错了，或内容已被移除。',
      hint: '返回首页，从菜单继续使用系统。',
    },
    serverError: {
      title: '服务器出错了',
      lead: '系统暂时无法完成请求。',
      hint: '请稍后重试；若反复出现请联系管理员。',
    },
    loading: {
      title: '加载中…',
      lead: '正在准备页面内容。',
    },
  },
}

/** 页脚短句：跟领域皮走，不另开随机轴 */
const FOOTER_TAGS = {
  library: '馆藏服务台',
  equipment: '设备借还窗口',
  asset: '物资台账入口',
  crm: '客户跟进台',
  event: '事件上报台',
  shop: '商城服务台',
  dorm: '宿舍事务窗口',
  property: '物业报修台',
  ithelp: 'IT 服务台',
  activity: '活动报名处',
  lostfound: '失物招领榜',
  course: '选课服务中心',
  food: '点餐服务台',
  hospital: '预约分诊入口',
  parking: '车位服务台',
  meeting: '场地预约台',
  salon: '预约前台',
  hotel: '客房服务台',
  media: '片库服务台',
  music: '曲库服务台',
  forum: '社区服务台',
  blog: '站点阅读台',
  generic: '在线服务入口',
}

const KIND_META = {
  '404': { code: '404', homeLabel: '返回首页' },
  '500': { code: '500', homeLabel: '返回首页', retryLabel: '重新加载' },
  loading: { code: '', homeLabel: '返回首页' },
}

export function domainFlavor(flavorId = getFlavor()) {
  const id = flavorId || 'generic'
  const base = FLAVORS[id] || FLAVORS.generic
  return {
    ...base,
    footerTag: FOOTER_TAGS[id] || FOOTER_TAGS.generic,
  }
}

/** 门户页脚：品牌名 + 领域短句 */
export function portalFooterCopy() {
  const delivered = getDelivered()
  const labels = schemaLabels()
  const flavor = domainFlavor()
  const domainLabel = getDomainLabel()
  return {
    brand: labels.appName || delivered.title || '本系统',
    tagline: flavor.footerTag || `${domainLabel}服务门户`,
  }
}

/** @param {'404'|'500'|'loading'} kind */
export function specialPageCopy(kind) {
  const delivered = getDelivered()
  const labels = schemaLabels()
  const appName = labels.appName || delivered.title || '本系统'
  const domainLabel = getDomainLabel()
  const flavor = domainFlavor()
  const block =
    kind === '500' ? flavor.serverError : kind === 'loading' ? flavor.loading : flavor.notFound
  const meta = KIND_META[kind] || KIND_META['404']
  return {
    kind,
    code: meta.code,
    motif: flavor.motif,
    appName,
    domainLabel,
    theme: delivered.theme || 'lib-ink',
    title: block.title,
    lead: block.lead,
    hint: block.hint || '',
    homeLabel: meta.homeLabel,
    retryLabel: meta.retryLabel || '',
  }
}
