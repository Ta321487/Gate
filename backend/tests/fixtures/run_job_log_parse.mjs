/**
 * pytest 调 Node：与控制台 jobLogRuns.js 同真源切段。
 * stdin：原始 job.log 文本；stdout：parseJobRuns JSON。
 */
import { parseJobRuns } from '../../../frontend/src/views/projectDetail/jobLogRuns.js'

let raw = ''
for await (const chunk of process.stdin) raw += chunk
const runs = parseJobRuns(raw)
process.stdout.write(
  JSON.stringify(
    runs.map((r) => ({
      outcome: r.outcome,
      body: r.body,
    })),
  ),
)
