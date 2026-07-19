/**
 * 工厂 bake 写入的交付配置（会打进 ZIP）。
 * 勿手改；重新生成项目时会被覆盖。
 */
export const FACTORY_DELIVERED = {
  title: '',
  theme: 'lib-ink',
  domain: 'DOM-GENERIC',
  domainLabel: '通用',
  authTemplate: 'split',
  authEntryMode: 'role_pick',
  authRoleWidget: 'radio',
  authHero: '',
  portalBanners: [],
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
