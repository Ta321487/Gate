<template>
  <div class="legal">
    <h1>用户协议</h1>
    <p>欢迎使用本系统。注册即表示您同意遵守以下约定：</p>
    <ol>
      <li>妥善保管账号与密码，不得将账号转借他人。</li>
      <li>提交的资料应真实、准确，不得发布违法或不当内容。</li>
      <li>管理员有权对违规账号采取停用等措施。</li>
      <li>本协议仅用于本系统使用说明，不构成对外法律文书审定文本。</li>
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
