<template>
  <div class="legal">
    <h1>隐私政策</h1>
    <p>我们仅在提供本系统服务所需范围内处理您的信息：</p>
    <ol>
      <li>收集范围：注册账号、联系方式及您主动填写的资料字段。</li>
      <li>用途：身份校验、业务办理与系统通知（含站内消息）。</li>
      <li>保存：信息保存在本系统数据库，不用于向第三方出售。</li>
      <li>您可在个人中心查看与更新资料，或申请注销账号。</li>
    </ol>
    <router-link to="/register">返回注册</router-link>
  </div>
</template>

<style scoped>
.legal {
  max-width: 720px;
  margin: 2rem auto;
  padding: 1.5rem;
  line-height: 1.7;
  color: #1e293b;
}
h1 { font-size: 1.4rem; margin-bottom: 1rem; }
ol { padding-left: 1.25rem; margin: 1rem 0 1.5rem; }
a { color: #0f766e; }
</style>
