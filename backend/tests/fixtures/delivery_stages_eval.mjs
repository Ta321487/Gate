/**
 * pytest 调 Node：与 frontend deliveryStages.js 同真源。
 */
import {
  buildDeliveryStages,
  canEnterDetailTab,
  defaultTabForStatus,
  defaultDeliveryArtifactView,
} from '../../../frontend/src/deliveryStages.js'

let raw = ''
for await (const chunk of process.stdin) raw += chunk
const body = JSON.parse(raw || '{}')
const kind = body.kind || 'stages'
if (kind === 'defaultTab') {
  process.stdout.write(JSON.stringify((body.statuses || []).map(defaultTabForStatus)))
} else if (kind === 'canEnter') {
  process.stdout.write(
    JSON.stringify(
      (body.cases || []).map((c) => canEnterDetailTab(c.p, c.tab)),
    ),
  )
} else if (kind === 'artifactView') {
  process.stdout.write(
    JSON.stringify((body.projects || []).map(defaultDeliveryArtifactView)),
  )
} else {
  process.stdout.write(
    JSON.stringify(
      (body.cases || []).map((c) =>
        buildDeliveryStages(c.p, c.activeTab || '').map((s) => ({
          key: s.key,
          state: s.state,
          locked: s.state === 'locked',
        })),
      ),
    ),
  )
}
