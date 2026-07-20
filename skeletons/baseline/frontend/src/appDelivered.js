/**
 * 课题交付配置（文案 / 菜单 / 能力）。由生成写入，一般无需手改。
 */
export const APP_DELIVERED = {
  title: '',
  theme: 'lib-ink',
  flavor: 'generic',
  domainLabel: '通用',
  traits: { addressBook: true },
  authTemplate: 'split',
  authEntryMode: 'role_pick',
  authRoleWidget: 'radio',
  authHero: '',
  portalBanners: [],
  portalGuestBrowse: false,
  guestTeaserLimit: 3,
  guestLoginCta: '',
  accept: 'reject',
  schema: {
    version: 1,
    title: '',
    capabilities: [],
    labels: {
      appName: '',
      authEyebrow: '欢迎使用',
      authLead: '验证码登录，开放注册；登录后可使用系统基础能力。',
      authPoints: ['验证码登录', '开放注册', '个人资料与头像'],
    },
    menus: { admin: [], user: [] },
    entities: {},
    seeds: {},
  },
}
