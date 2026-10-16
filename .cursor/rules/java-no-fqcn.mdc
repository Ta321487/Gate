---
description: Java 骨架禁止写全类名；用 import + 短名
globs: skeletons/**/*.java
alwaysApply: false
---

# Java：禁止写全类名

骨架与出包 Java **禁止**在方法体、字段类型、注解参数里写 `com.thesis...` / `java.util...` 全类名。

## DO

- 文件顶部 `import`，正文用短名：`AppPolicy`、`AdminAuth`、`HttpSession`、`List`、`Map`。
- 同包类直接短名；跨包先 import。

## DON'T

```java
// ❌
com.thesis.config.AppPolicy.SENSITIVE_CONFIRM
jakarta.servlet.http.HttpSession session
java.util.List.of()

// ✅
import com.thesis.config.AppPolicy;
import jakarta.servlet.http.HttpSession;
import java.util.List;
AppPolicy.SENSITIVE_CONFIRM
HttpSession session
List.of()
```

## 例外（仅这些）

- `package` 声明、`import` 行本身。
- 字符串里的类名（反射、文档注释里的 `{@link}` 可保留短名）。
- prune / 代码生成替换成的占位（如 `java.util.Map.of(...)`）属于既有擦除契约，**新写业务代码不要学**。
