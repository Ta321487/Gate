# Vue 大文件拆分批次（活表）

> **本文只负责**：骨架超大 `.vue` 外提同名 `.setup.js` + `.css` 的进度与护栏口径。  
> **不负责**：观感加厚、布局闸、控件选型（各见专题册）。  
> **状态**：**进行中** · 范式 `ArchiveBrowse` 已齐；按行数 ≥1000 排队，一轮一页。  
> **硬闸**：只搬家不改行为；断言须 **合读** `.vue` + `.setup.js`（必要时 + `.css`），禁止假绿。  
> **索引**：[README.md](./README.md) · 交接 [`../HANDOFF.md`](../HANDOFF.md) · 搁置 [`parked-work.md`](./parked-work.md)

---

## 0. 硬口径

| 规则 | 含义 |
|------|------|
| **修工厂** | 只改 `skeletons/baseline/frontend`；禁止只擦某一学生 ZIP |
| **只搬家** | `<script setup>` / `<style scoped>` 原样外提；不改模板、逻辑、文案 |
| **命名** | `Foo.vue` → 同目录 `Foo.setup.js` + `Foo.css` |
| **范式** | `<script setup src="./Foo.setup.js"></script>` + `<style scoped src="./Foo.css"></style>` |
| **合读护栏** | 测里凡读整页源码的，拆后须 `.vue`+`.setup.js` 拼接断言（对齐 `test_interact_thicken_features._archive_browse_src`） |
| **门槛** | 本批只拆约 **≥1000 行** 的页 |

## 1. 进度总表

| 序 | 文件 | 状态 |
|----|------|------|
| — | `views/user/ArchiveBrowse.vue` | **已齐**（范式） |
| 1 | `views/user/MyTickets.vue` | 待拆 |
| 2 | `views/admin/TicketsAdmin.vue` | 待拆 |
| 3 | `views/admin/ArchiveAdmin.vue` | 待拆 |
| 4 | `views/admin/TicketRecordsAdmin.vue` | 待拆 |
| 5 | `views/user/SlotBook.vue` | 待拆 |
| 6 | `views/user/PortalHome.vue` | 待拆 |
| 7 | `views/user/Cart.vue` | 待拆 |
| 8 | `views/Profile.vue` | 待拆 |
| 9 | `views/user/MyOrders.vue` | 待拆 |

## 2. 单页工序

1. 定位 `^<script setup>` / `^<style scoped>` 边界。  
2. 正文写入 `*.setup.js` / `*.css`（去掉外层标签）。  
3. `.vue` 只留 template + 两行 `src=` 引用。  
4. 跑该页相关 pytest；修「只读 .vue」为合读。  
5. 提交推送；更新本表状态；再开下一页。

## 3. 不做

- 不拆子组件 / composable（本批只外提 script/style）。  
- 不借拆分改观感、门禁、匹配。  
- 不一次多页合提。
