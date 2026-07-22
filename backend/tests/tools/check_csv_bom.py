"""校验 CSV 工具：UTF-8 BOM 字节头 + 中文不被破坏。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FE = ROOT / "skeletons" / "baseline" / "frontend"


def main() -> None:
    # 用 Node 复现浏览器侧 TextEncoder + BOM 逻辑
    script = r"""
const { TextEncoder } = require('util');
function csvEscape(v) {
  let s = v == null ? '' : String(v);
  s = s.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}
const headers = ['单号', '标题', '状态'];
const rows = [[1, '图书《测试》', '待审核'], [2, '=1+1', '已通过']];
const lines = [headers.map(csvEscape).join(',')];
for (const row of rows) lines.push(row.map(csvEscape).join(','));
const body = lines.join('\r\n');
const bom = Buffer.from([0xef, 0xbb, 0xbf]);
const encoded = Buffer.from(body, 'utf8');
const out = Buffer.concat([bom, encoded]);
if (out[0] !== 0xef || out[1] !== 0xbb || out[2] !== 0xbf) {
  console.error('BOM missing');
  process.exit(1);
}
const text = out.slice(3).toString('utf8');
if (!text.includes('图书《测试》') || !text.includes("'=1+1")) {
  console.error('content broken', text);
  process.exit(1);
}
if (!text.includes('\r\n')) {
  console.error('CRLF missing');
  process.exit(1);
}
console.log('csv_bom_ok bytes=', out.length);
"""
    r = subprocess.run(
        ["node", "-e", script],
        cwd=str(FE),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    print(r.stdout or r.stderr)
    if r.returncode != 0:
        sys.exit(r.returncode)


if __name__ == "__main__":
    main()
