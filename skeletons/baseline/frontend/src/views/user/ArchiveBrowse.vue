<template>
  <div>
    <section class="hero">
      <h1>{{ plural }}检索</h1>
      <p>
        按名称检索{{ playUrlField ? '、在线播放' : '' }}{{ bodyRich ? '、阅读正文' : '' }}，{{ actionHint }}。
        <template v-if="ruleHint"> {{ ruleHint }}</template>
      </p>
      <SchemaLabelHints :keys="browseHintKeys" />
      <p v-if="shelfAnnounceHint" class="page-hint">
        {{ shelfAnnounceHint }}
        <template v-if="favOn">可将新书/新物资点「收藏」登记意向。</template>
      </p>
      <p v-if="hotMode && hotRankOn" class="page-hint">
        {{ hotRankPageTitle }}：{{ hotRankPageLead }}
      </p>
      <p v-if="activeSectionNotice" class="page-hint section-notice">{{ activeSectionNotice }}</p>
      <p v-if="datingActivityEntryOn" class="page-hint">
        <strong v-if="datingActivityEntryTitle">{{ datingActivityEntryTitle }} · </strong>
        {{ datingActivityEntryHint }}
        <el-button link type="primary" @click="$router.push('/notices')">{{ datingActivityEntryCta }}</el-button>
      </p>
      <p v-if="mutualInterviewEntryOn" class="page-hint">
        <strong v-if="mutualInterviewEntryTitle">{{ mutualInterviewEntryTitle }} · </strong>
        {{ mutualInterviewEntryHint }}
        <el-button link type="primary" @click="$router.push('/notices')">{{ mutualInterviewEntryCta }}</el-button>
      </p>
      <div v-if="teamSkillTagsOn" class="search-extra" style="margin-top:8px">
        <el-input
          v-model="skillTagFilter"
          clearable
          :placeholder="skillTagsFilterPlaceholder"
          style="max-width:240px"
          @change="load"
          @clear="load"
        />
      </div>
      <p v-if="teamFullStageHint && interactThicken.mutualTeamFullClose" class="page-hint">{{ teamFullStageHint }}</p>
      <p v-if="carpoolFullStageHint && interactThicken.carpoolFullClose" class="page-hint">{{ carpoolFullStageHint }}</p>
      <p v-if="carpoolDupTripDeny && interactThicken.carpoolDupTripCheck" class="page-hint">{{ carpoolDupTripDeny }}</p>
      <div class="search">
        <!-- 顶栏已有 globalSearch 时不再摆第二格关键词，只留分类/价筛等 -->
        <el-autocomplete
          v-if="titleSuggestOn && !topBarSearchOn"
          v-model="keyword"
          clearable
          :fetch-suggestions="fetchSuggest"
          :placeholder="searchPlaceholder"
          style="flex:1; min-width:180px"
          @keyup.enter="load"
          @select="onSuggestSelect"
        />
        <el-input
          v-else-if="!topBarSearchOn"
          v-model="keyword"
          clearable
          :placeholder="searchPlaceholder"
          @keyup.enter="load"
        />
        <el-select
          v-if="!multiCategory"
          v-model="categoryId"
          clearable
          :placeholder="fieldLabel('category', '分类')"
          class="search-cat"
          @change="onCategoryChange"
        >
          <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-select
          v-else
          v-model="categoryIds"
          multiple
          collapse-tags
          collapse-tags-tooltip
          clearable
          :placeholder="fieldLabel('categoryIds', fieldLabel('category', '分类'))"
          class="search-cat"
          style="min-width:220px"
          @change="onMultiCategoryChange"
        >
          <el-option-group
            v-for="g in categoriesByDimension"
            :key="g.dimension || '未分组'"
            :label="g.dimension || '未分组'"
          >
            <el-option v-for="c in g.items" :key="c.id" :label="c.name" :value="c.id" />
          </el-option-group>
        </el-select>
        <el-select
          v-if="tagFilter"
          v-model="tagIds"
          multiple
          collapse-tags
          collapse-tags-tooltip
          clearable
          placeholder="标签（同时满足）"
          style="min-width:200px"
          @change="onTagFilterChange"
        >
          <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <el-select
          v-if="collegeFilterOn"
          v-model="collegeFilter"
          clearable
          filterable
          :placeholder="fieldLabel('college', '开课学院')"
          class="search-cat"
          @change="load"
        >
          <el-option v-for="c in collegeOptions" :key="c" :label="c" :value="c" />
        </el-select>
        <el-input
          v-if="artistAlbumFilterOn"
          v-model="artistFilter"
          clearable
          :placeholder="artistFilterPlaceholder"
          style="max-width:140px"
          @keyup.enter="load"
        />
        <el-input
          v-if="artistAlbumFilterOn"
          v-model="albumFilter"
          clearable
          :placeholder="albumFilterPlaceholder"
          style="max-width:140px"
          @keyup.enter="load"
        />
        <el-input
          v-if="datingIdealFilterOn"
          v-model="datingCityFilter"
          clearable
          :placeholder="datingFilterCityPlaceholder"
          style="max-width:140px"
          @keyup.enter="load"
        />
        <el-input-number
          v-if="datingIdealFilterOn"
          v-model="datingAgeMinFilter"
          class="search-num"
          :min="1"
          :max="99"
          :controls="false"
          :placeholder="datingFilterAgeMinPlaceholder"
        />
        <el-input-number
          v-if="datingIdealFilterOn"
          v-model="datingAgeMaxFilter"
          class="search-num"
          :min="1"
          :max="99"
          :controls="false"
          :placeholder="datingFilterAgeMaxPlaceholder"
        />
        <div v-if="priceRangeFilterOn" class="price-range" role="group" :aria-label="`${priceMinPlaceholder}-${priceMaxPlaceholder}`">
          <el-input-number
            v-model="priceMinFilter"
            class="price-range-num"
            :min="0"
            :precision="2"
            :step="1"
            :controls="false"
            :placeholder="priceMinPlaceholder"
            @change="load"
            @keyup.enter="load"
          />
          <span class="price-range-sep" aria-hidden="true">–</span>
          <el-input-number
            v-model="priceMaxFilter"
            class="price-range-num"
            :min="0"
            :precision="2"
            :step="1"
            :controls="false"
            :placeholder="priceMaxPlaceholder"
            @change="load"
            @keyup.enter="load"
          />
        </div>
        <el-button type="primary" size="small" class="search-submit" @click="load">搜索</el-button>
        <el-button
          v-if="hotRankOn"
          size="small"
          :type="hotMode ? 'warning' : 'default'"
          @click="toggleHotMode"
        >{{ hotMode ? hotRankBackLabel : hotRankToggleLabel }}</el-button>
        <el-button
          v-if="userPublish && !isGuest"
          size="small"
          @click="openPublish"
        >{{ publishCtaLabel }}</el-button>
      </div>
      <div v-if="archiveYearMonthOn" class="search ym-row">
        <el-select
          v-model="archiveYear"
          clearable
          :placeholder="archiveYearMonthLabel"
          class="search-cat"
          @change="onYearMonthChange"
        >
          <el-option
            v-for="y in archiveYearOptions"
            :key="y"
            :label="`${y} 年`"
            :value="y"
          />
        </el-select>
        <el-select
          v-model="archiveMonth"
          clearable
          :placeholder="archiveYearMonthAllLabel"
          class="search-cat"
          :disabled="!archiveYear"
          @change="load"
        >
          <el-option
            v-for="m in 12"
            :key="m"
            :label="`${m} 月`"
            :value="m"
          />
        </el-select>
      </div>
      <div v-if="categoryFollowOn && activeFollowCategoryId" class="follow-bar">
        <el-button
          v-if="!isGuest"
          size="small"
          :type="categoryFollowing ? 'warning' : 'default'"
          :loading="followLoading"
          @click="toggleCategoryFollow"
        >{{ categoryFollowing ? categoryUnfollowLabel : categoryFollowLabel }}</el-button>
        <span v-if="categoryFollowerCountOn" class="muted">
          {{ categoryFollowerCountLabel }} {{ categoryFollowerCount }}
        </span>
        <span v-if="categoryFollowHint" class="muted follow-hint">{{ categoryFollowHint }}</span>
      </div>
      <div v-if="friendLinksOn && friendLinks.length" class="friend-links">
        <span class="friend-lab">{{ friendLinkPageTitle }}</span>
        <a
          v-for="fl in friendLinks"
          :key="fl.id"
          class="friend-chip"
          :href="fl.url"
          target="_blank"
          rel="noopener noreferrer"
        >{{ fl.title }}</a>
      </div>
      <div v-if="authorPageOn && authorFilter" class="page-hint">
        {{ authorPageTitle }}：{{ authorFilter }}
        <el-button link type="primary" @click="clearAuthorFilter">全部文章</el-button>
      </div>
      <div v-if="shareCodeOn" class="share-bar">
        <el-input
          v-model="shareCodeInput"
          clearable
          :placeholder="shareCodePrompt"
          style="max-width:220px"
          @keyup.enter="openByShareCode"
        />
        <el-button @click="openByShareCode">{{ shareCodeEntryLabel }}</el-button>
      </div>
      <p v-if="coverWallActive" class="page-hint">{{ posterWallTitle }}：{{ posterWallLead }}</p>
      <div v-if="searchAssist && hotKeywords.length" class="hot">
        <span class="hot-lab">热搜</span>
        <button
          v-for="(w, i) in hotKeywords"
          :key="i"
          type="button"
          class="hot-chip"
          @click="applyHot(w)"
        >{{ w }}<span v-if="i < 3" class="hot-fire" aria-hidden="true">火</span></button>
      </div>
    </section>

    <RecommendStrip
      v-if="hasRecommend && !isGuest"
      ref="recRef"
      :apply-label="favOn && !showPrimaryApply ? '收藏' : primaryActionLabel"
      :exclude-ids="list.map((r) => r.id)"
      @apply="onRecommendApply"
    />

    <div class="list-hd">
      <h2>{{ plural }}列表</h2>
      <span class="list-hd-hint">检索与筛选结果</span>
    </div>
    <div
      class="browse-surface"
      :data-content-surface="contentSurface || 'cards'"
      :data-trade-surface="tradeSurface || 'cards'"
      :data-reserve-surface="reserveSurface || 'cards'"
      :data-borrow-surface="borrowSurface || 'cards'"
      :data-apply-surface="applySurface || 'cards'"
      :data-interact-surface="interactSurface || 'cards'"
      :data-follow-surface="followSurface || 'cards'"
      :class="{
        'is-splitdesk': contentSurface === 'splitdesk',
        'surface-shelfgrid': tradeSurface === 'shelfgrid',
        'surface-menuboard': tradeSurface === 'menuboard',
        'surface-showtime': tradeSurface === 'showtime',
        'surface-slotstrip': reserveSurface === 'slotstrip',
        'surface-roomstate': reserveSurface === 'roomstate',
        'surface-vehiclecard': reserveSurface === 'vehiclecard',
        'surface-bookshelf': borrowSurface === 'bookshelf',
        'surface-stockrow': borrowSurface === 'stockrow',
        'surface-bedblocks': borrowSurface === 'bedblocks',
        'surface-parcelshelf': borrowSurface === 'parcelshelf',
        'surface-eventposter': applySurface === 'eventposter',
        'surface-coursetable': applySurface === 'coursetable',
        'surface-noticeboard': applySurface === 'noticeboard',
        'surface-tourcard': applySurface === 'tourcard',
        'surface-profilegrid': interactSurface === 'profilegrid',
        'surface-mutualpick': interactSurface === 'mutualpick',
        'surface-triprow': interactSurface === 'triprow',
        'surface-pipeline': followSurface === 'pipeline',
        'surface-dossier': followSurface === 'dossier',
        'surface-listing': followSurface === 'listing',
      }"
    >
    <div
      class="grid"
      :class="{
        'poster-wall': coverWallActive,
        'surface-folio': contentSurface === 'folio',
        'surface-ledger': contentSurface === 'ledger',
        'surface-coverwall': coverWallActive,
        'surface-splitdesk-list': contentSurface === 'splitdesk',
      }"
    >
      <article
        v-for="(row, idx) in filteredList"
        :key="row.id"
        class="card imm-lift"
        :data-card-voice="cardVoice"
        :data-bed-tone="borrowBedTone(row)"
        :data-follow-tone="followStageToneOf(row)"
        :class="{
          'reported-dim': reportedIds.has(row.id),
          'poster-card': coverWallActive,
          'folio-hero': contentSurface === 'folio' && idx === 0,
          'split-active': contentSurface === 'splitdesk' && splitSelectedId === row.id,
          'bed-tone-free': borrowSurface === 'bedblocks' && borrowBedTone(row) === 'free',
          'bed-tone-busy': borrowSurface === 'bedblocks' && borrowBedTone(row) === 'busy',
          'bed-tone-hold': borrowSurface === 'bedblocks' && borrowBedTone(row) === 'hold',
          'stock-row-ok': borrowSurface === 'stockrow' && stockOk(row),
          'stock-row-out': borrowSurface === 'stockrow' && !stockOk(row),
          'room-tone-free': reserveSurface === 'roomstate' && reserveRoomTone(row) === 'free',
          'room-tone-busy': reserveSurface === 'roomstate' && reserveRoomTone(row) === 'busy',
          'room-tone-hold': reserveSurface === 'roomstate' && reserveRoomTone(row) === 'hold',
          'lost-tone-find': applySurface === 'noticeboard' && lostBoardTone(row) === 'find',
          'lost-tone-claim': applySurface === 'noticeboard' && lostBoardTone(row) === 'claim',
          'lost-tone-clue': applySurface === 'noticeboard' && lostBoardTone(row) === 'clue',
          'course-conflict': applySurface === 'coursetable' && conflictHighlightOn && wouldConflict(row),
          'seat-tight': applySurface === 'eventposter' && stockOk(row) && stockTight(row),
          'seat-full': applySurface === 'eventposter' && !stockOk(row),
          'trip-full': interactSurface === 'triprow' && !stockOk(row),
        }"
        @click="onContentSurfaceCardClick(row, $event)"
      >
        <div class="cover" :class="{ 'cover-fallback': !row.coverUrl }">
          <img v-if="row.coverUrl" :src="row.coverUrl" alt="" />
          <template v-else>{{ (row.title || '?').slice(0, 1) }}</template>
        </div>
        <div class="meta">
          <h3>
            {{ row.title }}
            <el-tag v-if="coverMarkOn && Number(row.isCover) === 1" size="small" type="warning" class="cover-tag">{{ coverMarkLabel }}</el-tag>
          </h3>
          <p
            v-if="(cardVoice === 'story' || contentSurface === 'folio' || applySurface === 'tourcard' || interactSurface === 'profilegrid') && storyLeadOf(row)"
            class="story-lead"
          >{{ storyLeadOf(row) }}</p>
          <p v-if="artistAlbumFilterOn && (row.artist || row.album)" class="sub">
            {{ [row.artist, row.album].filter(Boolean).join(' · ') }}
          </p>
          <p v-if="isBlindBox(row)" class="sub">盲盒 · {{ blindBoxLine(row) }}</p>
          <p v-if="purchaseGateOn && Number(row.needPermit) === 1" class="sub">需审核后才能购买</p>
          <p v-if="purchaseGateOn && Number(row.monthLimit) > 0" class="sub">每人每月限购 {{ row.monthLimit }} 件</p>
          <div v-if="cardVoice === 'board'" class="board-status">
            <StatusChip
              v-if="boardToneOf(row)"
              :tone="boardToneOf(row)"
              :label="boardLabelOf(row)"
            />
            <span v-else-if="quotaRemainOn && quotaRemainOf(row) != null" class="sched muted">
              {{ quotaRemainHint || '名额余量' }}：{{ quotaRemainOf(row) }}
            </span>
            <span v-else class="sched muted">{{ boardLabelOf(row) }}</span>
          </div>
          <p
            v-else-if="primarySignalOf(row)"
            class="main-signal"
            :class="{ price: authorFieldIsMoney }"
          >{{ primarySignalOf(row) }}</p>
          <p
            v-if="cardVoice === 'catalog' && !authorFieldIsMoney && categoryTextOf(row)"
            class="sub signal-cat"
          >{{ categoryTextOf(row) }}</p>
          <p v-if="marketplace && shopLabel(row)" class="sub shop">店铺：{{ shopLabel(row) }}</p>
          <p v-if="flashOn && row.promoActive" class="promo promo-bar">
            {{ flashBadge }} ¥{{ Number(row.promoPrice).toFixed(2) }}
            <span class="promo-list">原价 ¥{{ Number(row.listPriceYuan ?? row.author).toFixed(2) }}</span>
            <span
              v-if="flashCountdownText(row)"
              class="flash-cd"
              :class="{ 'cd-urgent': isUrgentCountdown(flashSecondsLeft(row), 300) }"
            > · {{ flashCountdownText(row) }}</span>
          </p>
          <div v-if="cardShortTags(row).length" class="short-tags">
            <span
              v-for="tag in cardShortTags(row)"
              :key="tag.key"
              class="short-tag"
            ><span v-if="tag.label" class="short-tag-k">{{ tag.label }}</span><span class="short-tag-v">{{ tag.text }}</span></span>
          </div>
          <p
            v-for="f in (cardVoice === 'story' ? cardPreviewFields : [])"
            :key="f.key"
            class="detail-line muted"
          ><span class="k">{{ f.label }}</span>：{{ formatFieldValue(row, f) }}</p>
          <p v-if="row.tagNames?.length" class="sched muted">
            <template v-if="tagColorOn">
              <span
                v-for="(name, i) in row.tagNames"
                :key="name + i"
                class="tag-chip"
              >
                <span class="tag-dot" :style="{ background: tagColor(name) }" />{{ name }}
              </span>
            </template>
            <template v-else>{{ row.tagNames.join(' · ') }}</template>
          </p>
          <p v-if="intentCountOn && intentCountOf(row) != null" class="sched muted">
            {{ intentCountHint || '意向' }}：{{ intentCountOf(row) }}
          </p>
          <p v-if="cardVoice !== 'board' && quotaRemainOn && quotaRemainOf(row) != null" class="sched muted">
            {{ quotaRemainHint || '名额余量' }}：{{ quotaRemainOf(row) }}
          </p>
          <div v-if="tutorQuotaBarOn && tutorQuotaPercent(row) != null" class="quota-bar">
            <span class="muted">{{ tutorQuotaBarLabel }} {{ tutorQuotaText(row) }}</span>
            <el-progress
              :percentage="tutorQuotaPercent(row)"
              :stroke-width="8"
              :show-text="false"
            />
            <span v-if="tutorQuotaBarHint" class="muted tiny">{{ tutorQuotaBarHint }}</span>
          </div>
          <p v-if="carpoolSeatRemainOn && row.stock != null" class="sched muted">
            {{ carpoolSeatRemainLabel }}：{{ row.stock }}
            <span v-if="carpoolSeatRemainHint" class="tiny"> · {{ carpoolSeatRemainHint }}</span>
          </p>
          <p v-if="carpoolCampusDictOn && (row.startCampus || row.endCampus)" class="sched muted">
            {{ carpoolCampusStartLabel }} {{ row.startCampus || '—' }}
            → {{ carpoolCampusEndLabel }} {{ row.endCampus || '—' }}
          </p>
          <p v-if="carpoolViaPointsOn && row.viaPoints" class="sched muted">
            {{ carpoolViaPointsLabel }}：{{ row.viaPoints }}
          </p>
          <p v-if="carpoolShareNoteOn && row.shareNote" class="sched muted">
            {{ carpoolShareNoteLabel }}：{{ row.shareNote }}
          </p>
          <p v-if="carpoolPrefNoteOn && row.prefNote" class="sched muted">
            {{ carpoolPrefNoteLabel }}：{{ row.prefNote }}
          </p>
          <p v-if="carpoolLuggageOn && Number(row.luggageCount) > 0" class="sched muted">
            {{ carpoolLuggageCountLabel }}：{{ row.luggageCount }}
          </p>
          <p v-if="carpoolAaCalcOn && aaPerPerson(row) != null" class="sched muted">
            {{ carpoolAaLabel }}：约 {{ aaPerPerson(row) }} 元/人
            <span v-if="carpoolAaHint" class="tiny"> · {{ carpoolAaHint }}</span>
          </p>
          <p v-if="teamSkillTagsOn && skillTagsOf(row).length" class="sched muted">
            {{ skillTagsLabel }}：{{ skillTagsOf(row).join(' · ') }}
          </p>
          <p v-if="teamSkillMatchOn && skillMatchCount(row) != null" class="sched muted">
            {{ teamSkillMatchLabel }}：重合 {{ skillMatchCount(row) }} 项
          </p>
          <p v-if="row.mutexCode" class="sched muted">互斥组 {{ row.mutexCode }}</p>
          <p v-if="scheduleText(row)" class="sched">{{ scheduleText(row) }}</p>
          <p v-if="conflictHighlightOn && wouldConflict(row)" class="sched conflict-row">{{ conflictHighlightLabel }}：{{ conflictHighlightHint }}</p>
          <RichTextView v-if="bodyRich && row.isbn" class="excerpt" :html="row.isbn" compact />
          <div class="card-foot">
            <!--
              货架（shelfgrid）不露「另有 N 项」——真实货架无此元信息，详情钮已覆盖。
              其它表面仍挂底栏顶，禁回短签后（齐底空会顶在链接下）。
            -->
            <button
              v-if="cardMoreFieldCount > 0 && tradeSurface !== 'shelfgrid'"
              type="button"
              class="more-hint"
              @click.stop="openDetail(row)"
            >另有 {{ cardMoreFieldCount }} 项，见详情</button>
            <div class="card-meta">
              <span
                v-if="showStageChip"
                class="stage-chip"
                :data-stage="stageTone(row.stage)"
              >{{ row.stage || '—' }}</span>
              <el-tag
                v-if="Number(row.pinTop) === 1"
                size="small"
                type="warning"
                effect="plain"
              >{{ pinTopLabel }}</el-tag>
              <el-tag
                v-if="essenceOn && Number(row.essence) === 1"
                size="small"
                type="success"
                effect="plain"
              >{{ essenceLabel }}</el-tag>
              <el-tag
                v-if="lockedOn && Number(row.locked) === 1"
                size="small"
                type="info"
                effect="plain"
              >{{ lockedLabel }}</el-tag>
              <el-tag
                v-if="stockDisplay !== 'hidden'"
                :type="stockOk(row) ? (stockTight(row) ? 'warning' : 'success') : 'info'"
                size="small"
                effect="plain"
                :class="{ 'stock-tight': stockTight(row) }"
              >
                {{ stockText(row) }}
              </el-tag>
              <span
                v-if="stockTightHint && stockTight(row) && stockOk(row)"
                class="meta-hint"
              >{{ stockTightHint }}</span>
              <span
                v-if="minGroupHintOf(row)"
                class="meta-hint"
              >{{ minGroupHintOf(row) }}</span>
              <span
                v-if="row.courseKind"
                class="meta-hint"
              >{{ row.courseKind }}</span>
              <span
                v-if="row.sessionGroup"
                class="meta-hint"
              >场次 {{ row.sessionGroup }}</span>
              <span
                v-if="row.college"
                class="meta-hint"
              >{{ row.college }}</span>
              <span
                v-if="row.lostCategory"
                class="meta-hint"
              >{{ row.lostCategory }}</span>
              <span
                v-if="viewCountOn || Number(row.viewCount) > 0"
                class="meta-hint"
              >{{ viewCountLabel }} {{ Number(row.viewCount) || 0 }}</span>
              <span
                v-if="downloadCountOn && Number(row.downloadCount) > 0"
                class="meta-hint"
              >{{ downloadCountLabel }} {{ row.downloadCount }}</span>
              <a
                v-if="row.planUrl"
                class="meta-link"
                :href="row.planUrl"
                target="_blank"
                rel="noopener noreferrer"
                @click.stop
              >培养方案</a>
            </div>
            <div class="card-acts">
              <el-button
                v-if="showPrimaryApply"
                class="act-primary"
                size="small"
                type="primary"
                :disabled="!isSlotMode && !canApplyOrWait(row)"
                @click="onPrimary(row)"
              >{{ applyActionLabel(row) }}</el-button>
              <el-button
                v-if="playUrlOf(row)"
                class="act-secondary"
                size="small"
                @click="play(row)"
              >播放</el-button>
              <el-button
                v-if="showDetailBtn"
                class="act-secondary"
                size="small"
                @click="openDetail(row)"
              >{{ bodyRich ? '阅读' : '详情' }}</el-button>
              <el-button
                v-if="teamInviteOn"
                class="act-secondary"
                size="small"
                plain
                @click="sendTeamInvite(row)"
              >{{ teamInviteLabel }}</el-button>
              <el-button
                v-if="favOn && !isGuest"
                class="act-secondary"
                size="small"
                :type="favIds.includes(row.id) ? 'warning' : 'default'"
                :class="{ 'like-pulse': favPulseId === row.id }"
                @click="toggleFav(row)"
              >{{ favIds.includes(row.id) ? favoritedVerb : favoritesVerb }}</el-button>
              <el-button
                v-if="datingUserFollowOn && !isGuest && authorKey(row)"
                class="act-secondary"
                size="small"
                @click="toggleFollowUser(authorKey(row))"
              >{{ followBtnLabel(authorKey(row)) }}</el-button>
              <el-button
                v-if="likeOn && !isGuest"
                class="act-secondary"
                size="small"
                :type="likeIds.includes(row.id) ? 'warning' : 'default'"
                :class="{ 'like-pulse': likePulseId === row.id }"
                @click="toggleLike(row)"
              >
                {{ likeIds.includes(row.id) ? likedVerb : likeVerb }}{{ likeCountText(row) }}
                <StatusChip v-if="Number(row.likeCount) > 0" tone="warn" compact />
              </el-button>
              <el-button
                v-if="reportOn && !isGuest"
                class="act-secondary"
                size="small"
                :disabled="reportedIds.has(row.id)"
                @click="openReport(row)"
              >{{ reportedIds.has(row.id) ? '已举报' : reportVerb }}</el-button>
            </div>
          </div>
        </div>
      </article>
    </div>
    <aside
      v-if="contentSurface === 'splitdesk' && splitSelected && !splitNarrow"
      class="splitdesk-pane"
    >
      <div class="cover splitdesk-cover" :class="{ 'cover-fallback': !splitSelected.coverUrl }">
        <img v-if="splitSelected.coverUrl" :src="splitSelected.coverUrl" alt="" />
        <template v-else>{{ (splitSelected.title || '?').slice(0, 1) }}</template>
      </div>
      <h3>{{ splitSelected.title }}</h3>
      <p class="sub">
        {{ formatAuthor(splitSelected.author) }} ·
        {{
          (splitSelected.categoryNames?.length
            ? splitSelected.categoryNames.join(' · ')
            : splitSelected.categoryName) || '未分类'
        }}
      </p>
      <p
        v-if="viewCountOn || Number(splitSelected.viewCount) > 0"
        class="sched muted"
      >{{ viewCountLabel }} {{ Number(splitSelected.viewCount) || 0 }}</p>
      <p v-if="storyLeadOf(splitSelected)" class="splitdesk-lead">{{ storyLeadOf(splitSelected) }}</p>
      <RichTextView
        v-if="bodyRich && splitSelected.isbn"
        class="excerpt"
        :html="splitSelected.isbn"
        compact
      />
      <div class="row">
        <el-button
          size="small"
          type="primary"
          @click="router.push({ path: `/archive/item/${splitSelected.id}` })"
        >
          {{ bodyRich ? '阅读全文' : '打开详情' }}
        </el-button>
        <el-button
          v-if="favOn && !isGuest"
          size="small"
          :type="favIds.includes(splitSelected.id) ? 'warning' : 'default'"
          @click="toggleFav(splitSelected)"
        >{{ favIds.includes(splitSelected.id) ? favoritedVerb : favoritesVerb }}</el-button>
        <el-button
          v-if="likeOn && !isGuest"
          size="small"
          :type="likeIds.includes(splitSelected.id) ? 'warning' : 'default'"
          @click="toggleLike(splitSelected)"
        >{{ likeIds.includes(splitSelected.id) ? likedVerb : likeVerb }}{{ likeCountText(splitSelected) }}</el-button>
      </div>
    </aside>
    </div>

    <EmptyHint
      v-if="!list.length"
      title="暂无记录"
      desc="换个关键词试试，或去看看推荐。"
      mark="览"
    />
    <div v-if="!isGuest" class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        :total="total"
        @current-change="load"
        @size-change="load"
      />
    </div>
    <GuestLoginHint />

    <el-drawer v-model="detailVisible" :title="detail?.title || '详情'" size="520px" destroy-on-close>
      <template v-if="detail">
        <p v-if="datingUserFollowOn && authorKey(detail) && !isGuest" class="detail-line">
          <el-button size="small" type="primary" plain @click="toggleFollowUser(authorKey(detail))">
            {{ followBtnLabel(authorKey(detail)) }}
          </el-button>
        </p>
        <p v-if="datingAlbumAuditOn && detail.albumHidden" class="muted">{{ albumAuditHiddenHint }}</p>
        <div v-if="galleryUrls.length > 1" class="gallery">
          <el-carousel height="220px" indicator-position="outside">
            <el-carousel-item v-for="(u, i) in galleryUrls" :key="i">
              <el-image
                :src="u"
                class="detail-cover"
                fit="cover"
                :preview-src-list="galleryUrls"
                :initial-index="i"
                preview-teleported
              />
            </el-carousel-item>
          </el-carousel>
        </div>
        <el-image
          v-else-if="galleryUrls.length === 1"
          :src="galleryUrls[0]"
          class="detail-cover"
          fit="cover"
          :preview-src-list="galleryUrls"
          preview-teleported
        />
        <p class="sub">
          <template v-if="authorPageOn && authorKey(detail)">
            <el-button link type="primary" @click="openAuthorPage(detail)">
              {{ formatAuthor(detail.author) || authorKey(detail) }} · {{ authorPageEntryLabel }}
            </el-button>
          </template>
          <template v-else>{{ formatAuthor(detail.author) }}</template>
          ·
          {{
            (detail.categoryNames?.length ? detail.categoryNames.join(' · ') : detail.categoryName)
              || '未分类'
          }}
        </p>
        <el-tag v-if="Number(detail.pinTop) === 1" size="small" type="warning" effect="plain" style="margin-bottom:8px">{{ pinTopLabel }}</el-tag>
        <el-tag v-if="essenceOn && Number(detail.essence) === 1" size="small" type="success" effect="plain" style="margin:0 0 8px 6px">{{ essenceLabel }}</el-tag>
        <el-tag v-if="lockedOn && Number(detail.locked) === 1" size="small" type="info" effect="plain" style="margin:0 0 8px 6px">{{ lockedLabel }}</el-tag>
        <el-tag
          v-if="originKindOn && detail.originKind"
          size="small"
          effect="plain"
          style="margin:0 0 8px 6px"
        >{{ originKindText(detail.originKind) }}</el-tag>
        <p v-if="pinTopHint && Number(detail.pinTop) === 1" class="detail-line muted">{{ pinTopHint }}</p>
        <p v-if="essenceHint && Number(detail.essence) === 1" class="detail-line muted">{{ essenceHint }}</p>
        <p v-if="lockedHint && Number(detail.locked) === 1" class="detail-line muted">{{ lockedHint }}</p>
        <div v-if="accessPasswordOn && detail.contentLocked" class="pw-box">
          <p class="detail-line">{{ accessPasswordPrompt }}</p>
          <p v-if="accessPasswordHint" class="muted">{{ accessPasswordHint }}</p>
          <div class="pw-row">
            <el-input
              v-model="unlockPassword"
              type="password"
              show-password
              maxlength="64"
              :placeholder="accessPasswordLabel"
              style="flex:1"
              @keyup.enter="unlockDetail"
            />
            <el-button type="primary" :loading="unlockLoading" @click="unlockDetail">{{ accessPasswordUnlockLabel }}</el-button>
          </div>
        </div>
        <div v-if="seriesNavOn && (seriesPrev || seriesNext)" class="series-nav">
          <el-button v-if="seriesPrev" link type="primary" @click="openDetail(seriesPrev)">{{ seriesPrevLabel }}：{{ seriesPrev.title }}</el-button>
          <el-button v-if="seriesNext" link type="primary" @click="openDetail(seriesNext)">{{ seriesNextLabel }}：{{ seriesNext.title }}</el-button>
          <p v-if="seriesHint" class="muted">{{ seriesHint }}</p>
        </div>
        <section v-if="episodeListOn && detail.id" class="episode-box">
          <h4>{{ episodeListTitle }}</h4>
          <p v-if="!episodes.length" class="muted">{{ episodeListEmpty }}</p>
          <ul v-else class="episode-list">
            <li
              v-for="ep in episodes"
              :key="ep.id"
              :class="{ active: Number(activeEpisodeId) === Number(ep.id) }"
            >
              <button type="button" class="ep-btn" @click="selectEpisode(ep)">
                {{ ep.title }}
                <span v-if="epProgress(ep)?.completed" class="ep-done">{{ episodeCompletedLabel }}</span>
              </button>
            </li>
          </ul>
          <div v-if="playProgressOn && !isGuest" class="progress-row">
            <p v-if="playProgressHint" class="muted">{{ playProgressHint }}</p>
            <el-input-number v-model="progressSec" :min="0" :max="999999" controls-position="right" />
            <el-button size="small" :loading="progressSaving" @click="saveProgress(false)">{{ playProgressSaveLabel }}</el-button>
            <el-button size="small" type="success" :loading="progressSaving" @click="saveProgress(true)">{{ episodeCompletedLabel }}</el-button>
            <span v-if="currentProgress?.positionSec" class="muted">{{ episodeContinueLabel }} {{ currentProgress.positionSec }}s</span>
          </div>
        </section>
        <div v-if="playProgressOn && !episodeListOn && !isGuest && detail.id" class="progress-row">
          <p v-if="playProgressHint" class="muted">{{ playProgressHint }}</p>
          <el-input-number v-model="progressSec" :min="0" :max="999999" controls-position="right" />
          <el-button size="small" :loading="progressSaving" @click="saveProgress(false)">{{ playProgressSaveLabel }}</el-button>
          <el-button size="small" type="success" :loading="progressSaving" @click="saveProgress(true)">{{ episodeCompletedLabel }}</el-button>
          <span v-if="currentProgress?.positionSec" class="muted">{{ episodeContinueLabel }} {{ currentProgress.positionSec }}s</span>
        </div>
        <div v-if="audioQualityOn" class="audio-quality">
          <span class="aq-lab">{{ audioQualityLabel }}</span>
          <el-radio-group v-model="audioQualityPick" size="small">
            <el-radio-button v-for="opt in audioQualityOptions" :key="opt" :value="opt">{{ opt }}</el-radio-button>
          </el-radio-group>
          <p v-if="audioQualityHint" class="muted">{{ audioQualityHint }}</p>
        </div>
        <section v-if="lyricsOn && detail.id" class="lyrics-box">
          <h4>{{ lyricsLabel }}</h4>
          <pre v-if="detail.lyrics" class="lyrics-text">{{ detail.lyrics }}</pre>
          <p v-else class="muted">{{ lyricsEmpty }}</p>
        </section>
        <p v-if="coverMarkOn && Number(detail.isCover) === 1" class="detail-line">{{ coverMarkLabel }}</p>
        <p v-if="shareCodeOn && detail.shareCode" class="detail-line">{{ shareCodeLabel }}：{{ detail.shareCode }}</p>
        <p v-if="playCountOn && detail.playCount != null" class="detail-line">{{ playCountLabel }}：{{ detail.playCount }}</p>
        <CodeQrBlock
          v-if="codeQrOn && detail.checkinCode"
          :code="detail.checkinCode"
          :label="checkinCodeLabel"
        />
        <div v-if="lotteryResultOn && lotteryRows.length" class="lottery-box">
          <h4>{{ lotteryResultTitle }}</h4>
          <p v-if="lotteryResultHint" class="muted">{{ lotteryResultHint }}</p>
          <ul>
            <li v-for="r in lotteryRows" :key="r.id">{{ r.username }} · {{ r.status }}</li>
          </ul>
        </div>
        <p v-if="tagFilter && detail.tagNames?.length" class="detail-line">
          标签：{{ detail.tagNames.join(' · ') }}
        </p>
        <p v-if="marketplace && shopLabel(detail)" class="detail-line">店铺：{{ shopLabel(detail) }}</p>
        <p v-if="flashOn && detail.promoActive" class="promo">
          {{ flashBadge }} ¥{{ Number(detail.promoPrice).toFixed(2) }}
          <span class="promo-list">原价 ¥{{ Number(detail.listPriceYuan ?? detail.author).toFixed(2) }}</span>
          <span
            v-if="flashCountdownText(detail)"
            class="flash-cd"
            :class="{ 'cd-urgent': isUrgentCountdown(flashSecondsLeft(detail), 300) }"
          > · {{ flashCountdownText(detail) }}</span>
        </p>
        <el-tabs v-if="productSpecOn && productSpecText(detail)" class="detail-tabs">
          <el-tab-pane label="详情" name="detail">
            <p
              v-for="f in cardDetailFields"
              :key="f.key"
              class="detail-line"
            >{{ f.label }}：{{ formatFieldValue(detail, f) }}</p>
            <p v-if="scheduleText(detail)" class="sched">{{ scheduleText(detail) }}</p>
            <p v-if="detail.applyDeadlineAt" class="sched muted">
              {{ applyDeadlineLabel }} {{ detail.applyDeadlineAt }}
              <template v-if="mutualDeadlineText(detail)"> · {{ mutualDeadlineText(detail) }}</template>
            </p>
            <p v-if="mutualDeadlineHint && detail.applyDeadlineAt" class="sched muted">{{ mutualDeadlineHint }}</p>
            <p v-if="mutualIntroPackOn && detail.introPackUrl" class="sched">
              {{ introPackLabel }}：
              <a :href="detail.introPackUrl" target="_blank" rel="noopener">{{ introPackOpenLabel }}</a>
              <span v-if="introPackHint" class="muted"> · {{ introPackHint }}</span>
            </p>
          </el-tab-pane>
          <el-tab-pane :label="productSpecLabel" name="spec">
            <p class="detail-line">{{ productSpecText(detail) }}</p>
          </el-tab-pane>
        </el-tabs>
        <template v-else>
          <p
            v-for="f in cardDetailFields"
            :key="f.key"
            class="detail-line"
          >{{ f.label }}：{{ formatFieldValue(detail, f) }}</p>
          <p v-if="scheduleText(detail)" class="sched">{{ scheduleText(detail) }}</p>
          <p v-if="detail.applyDeadlineAt" class="sched muted">
            {{ applyDeadlineLabel }} {{ detail.applyDeadlineAt }}
            <template v-if="mutualDeadlineText(detail)"> · {{ mutualDeadlineText(detail) }}</template>
          </p>
          <p v-if="mutualDeadlineHint && detail.applyDeadlineAt" class="sched muted">{{ mutualDeadlineHint }}</p>
          <p v-if="mutualIntroPackOn && detail.introPackUrl" class="sched">
            {{ introPackLabel }}：
            <a :href="detail.introPackUrl" target="_blank" rel="noopener">{{ introPackOpenLabel }}</a>
            <span v-if="introPackHint" class="muted"> · {{ introPackHint }}</span>
          </p>
        </template>
        <div v-if="roomEquipOn && detailEquipNames.length" class="equip">
          <p class="equip-title">{{ equipSectionTitle }}</p>
          <el-tag
            v-for="n in detailEquipNames"
            :key="n"
            size="small"
            effect="plain"
            class="equip-tag"
          >
            <span class="equip-ico" aria-hidden="true">{{ equipmentMark(n) }}</span>
            {{ n }}
          </el-tag>
        </div>
        <RichTextView v-if="bodyRich && !detail.contentLocked" :html="detail.isbn || ''" />
        <div v-if="lostClueOn" class="thread">
          <h4 class="thread-title">线索留言</h4>
          <el-form label-position="top" class="alog-form" @submit.prevent>
            <el-form-item v-if="isGuest" label="称呼" required>
              <el-input v-model="clueForm.guestName" maxlength="32" placeholder="游客称呼" />
            </el-form-item>
            <el-form-item v-if="isGuest" label="联系方式">
              <el-input v-model="clueForm.guestContact" maxlength="64" placeholder="选填" />
            </el-form-item>
            <el-form-item label="类型">
              <el-radio-group v-model="clueForm.type">
                <el-radio value="clue">线索</el-radio>
                <el-radio value="ask">询问</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="内容" required>
              <el-input v-model="clueForm.content" type="textarea" :rows="2" maxlength="500" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="clueSubmitting" @click="submitClue">发表</el-button>
            </el-form-item>
          </el-form>
          <div v-if="clueLoading" class="thread-empty muted">加载中…</div>
          <div v-else-if="!clueList.length" class="thread-empty muted">暂无线索</div>
          <article v-for="r in clueList" :key="r.id" class="thread-item">
            <p class="thread-meta">
              <span>{{ r.userId || r.guestName || '路人' }}</span>
              <el-tag size="small" effect="plain">{{ r.type === 'ask' ? '询问' : '线索' }}</el-tag>
              <span class="muted">{{ r.createdAt || '' }}</span>
            </p>
            <p>{{ r.content }}</p>
          </article>
        </div>
        <div v-if="showThread" class="thread">
          <h4 class="thread-title">{{ threadTitle }}</h4>
          <p v-if="nestedReplyOn && mentionNotifyHint" class="muted" style="font-size:12px;margin:0 0 8px">{{ mentionNotifyHint }}</p>
          <div v-if="threadLoading" class="thread-empty muted">加载中…</div>
          <div v-else-if="!threadRoots.length" class="thread-empty muted">暂无回复</div>
          <article v-for="r in visibleThreadRoots" :key="r.id" class="thread-item">
            <p class="thread-meta">
              <span>{{ r.username || '用户' }}</span>
              <span class="muted">{{ r.approveAt || r.applyAt || '' }}</span>
              <el-button
                v-if="nestedReplyOn && !isGuest && !r.parentTicketId"
                link
                type="primary"
                size="small"
                @click="openNestedReply(r)"
              >{{ nestedReplyLabel }}</el-button>
              <el-button
                v-if="reportOn && !isGuest"
                link
                type="danger"
                size="small"
                @click="openReport(r, 'ticket')"
              >{{ reportVerb }}</el-button>
            </p>
            <RichTextView v-if="r.remark" :html="r.remark" />
            <p v-else class="muted">（无内容）</p>
            <div v-if="childrenOf(r.id).length" class="thread-children">
              <article v-for="c in childrenOf(r.id)" :key="c.id" class="thread-item nested">
                <p class="thread-meta">
                  <span>{{ c.username || '用户' }}</span>
                  <span class="muted">{{ c.approveAt || c.applyAt || '' }}</span>
                </p>
                <RichTextView v-if="c.remark" :html="c.remark" />
                <p v-else class="muted">（无内容）</p>
              </article>
            </div>
          </article>
          <el-button
            v-if="commentFoldOn && threadRoots.length > commentFoldAfter && !threadExpanded"
            link
            type="primary"
            @click="threadExpanded = true"
          >{{ commentFoldMoreLabel }}（{{ threadRoots.length - commentFoldAfter }}）</el-button>
          <el-button
            v-else-if="commentFoldOn && threadExpanded && threadRoots.length > commentFoldAfter"
            link
            @click="threadExpanded = false"
          >{{ commentFoldLessLabel }}</el-button>
        </div>
        <div v-if="logOn && !isGuest" class="alog">
          <h4 class="thread-title">{{ logSectionTitle }}</h4>
          <el-form label-position="top" class="alog-form" @submit.prevent>
            <el-form-item
              v-for="f in logFields"
              :key="f.key"
              :label="f.label || f.key"
            >
              <ArchiveFieldControl
                :field="f"
                v-model="logForm.payload[f.key]"
              />
            </el-form-item>
            <el-form-item label="异常">
              <el-switch v-model="logForm.abnormal" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="logSubmitting" @click="submitLog">{{ logSubmitLabel }}</el-button>
            </el-form-item>
          </el-form>
          <div v-if="logLoading" class="thread-empty muted">加载中…</div>
          <div v-else-if="!logList.length" class="thread-empty muted">暂无记录</div>
          <article v-for="r in logList" :key="r.id" class="thread-item">
            <p class="thread-meta">
              <span>{{ r.logDate }} · {{ r.username || '—' }}</span>
              <el-tag v-if="r.abnormal" type="danger" size="small" effect="plain">异常</el-tag>
            </p>
            <p class="detail-line">{{ logPayloadText(r) }}</p>
            <p v-if="r.remark" class="muted">{{ r.remark }}</p>
          </article>
        </div>
        <div class="drawer-acts">
          <el-button
            v-if="showPrimaryApply"
            type="primary"
            :disabled="!isSlotMode && !canApplyOrWait(detail)"
            @click="onPrimary(detail)"
          >{{ applyActionLabel(detail) }}</el-button>
          <el-button
            v-if="favOn && !isGuest"
            :type="favIds.includes(detail.id) ? 'warning' : 'default'"
            @click="toggleFav(detail)"
          >{{ favIds.includes(detail.id) ? favoritedVerb : favoritesVerb }}</el-button>
          <el-button
            v-if="likeOn && !isGuest"
            :type="likeIds.includes(detail.id) ? 'warning' : 'default'"
            @click="toggleLike(detail)"
          >{{ likeIds.includes(detail.id) ? likedVerb : likeVerb }}{{ likeCountText(detail) }}</el-button>
          <el-button
            v-if="reportOn && !isGuest"
            @click="openReport(detail)"
          >{{ reportVerb }}</el-button>
          <el-button
            v-if="stockNotifyOn && !isGuest && detail.id && !stockOk(detail)"
            type="warning"
            :loading="stockNotifyLoading"
            @click="subscribeStockNotify(detail)"
          >{{ stockNotifySubscribed
            ? (browseLabels.stockNotifyAgainLabel || browseLabels.stockNotifyDoneLabel || '再次订阅到货')
            : (browseLabels.stockNotifyLabel || '到货通知我') }}</el-button>
        </div>
        <p v-if="presaleNoteOn && detail.presaleNote" class="detail-line">{{ browseLabels.presaleNoteLabel || '预售说明' }}：{{ detail.presaleNote }}</p>
        <section v-if="specStockOn && siblingSpecs.length" class="item-spec-stock">
          <h4>{{ browseLabels.specStockLabel || '规格库存' }}</h4>
          <p v-if="browseLabels.specStockHint" class="muted">{{ browseLabels.specStockHint }}</p>
          <ul>
            <li v-for="s in siblingSpecs" :key="s.id">
              {{ s.specNote || s.title }} · 库存 {{ s.stock }}
            </li>
          </ul>
        </section>
        <section v-if="reviewOn && detail.id" class="item-reviews">
          <h4>用户评价</h4>
          <p v-if="goodRateOn" class="good-rate">
            <template v-if="itemGoodRate != null">{{ browseLabels.goodRateLabel || '好评率' }} {{ itemGoodRate }}%</template>
            <template v-else>{{ browseLabels.goodRateEmpty || '暂无评价' }}</template>
          </p>
          <div v-if="!itemReviews.length" class="muted">暂无评价</div>
          <article v-for="rv in itemReviews" :key="rv.id" class="rv">
            <div class="rv-hd">
              <el-rate :model-value="rv.rating" disabled />
              <span class="muted">{{ rv.displayName || rv.username || '用户' }} · {{ rv.createdAt }}</span>
            </div>
            <p>{{ rv.body || '（无文字）' }}</p>
            <el-image
              v-if="rv.imageUrl"
              :src="rv.imageUrl"
              fit="cover"
              style="width:72px;height:72px;border-radius:6px;margin-top:6px"
              :preview-src-list="[rv.imageUrl]"
            />
            <p v-if="rv.followBody" class="rv-follow">追评：{{ rv.followBody }}</p>
            <p v-if="rv.reply" class="rv-reply">商家回复：{{ rv.reply }}</p>
          </article>
        </section>
        <section v-if="itemQaOn && detail.id" class="item-qa">
          <h4>{{ browseLabels.itemQaLabel || '商品问答' }}</h4>
          <p v-if="browseLabels.itemQaHint" class="muted">{{ browseLabels.itemQaHint }}</p>
          <div v-if="!isGuest" class="ic-compose">
            <el-input
              v-model="itemQaDraft"
              type="textarea"
              :rows="2"
              maxlength="500"
              show-word-limit
              placeholder="对这件商品提问…"
            />
            <el-button type="primary" size="small" :loading="itemQaSubmitting" @click="submitItemQa">
              {{ browseLabels.itemQaSubmitLabel || '提问' }}
            </el-button>
          </div>
          <div v-else class="muted">登录后可提问</div>
          <div v-if="!itemQaList.length" class="muted">{{ browseLabels.itemQaEmpty || '还没有人提问' }}</div>
          <article v-for="q in itemQaList" :key="q.id" class="ic">
            <p class="ic-meta"><span>{{ q.nickname || q.username || '用户' }} · {{ q.createdAt }}</span></p>
            <p>{{ q.body || '（无文字）' }}</p>
            <p v-if="q.reply" class="rv-reply">回复：{{ q.reply }}</p>
          </article>
        </section>
        <p v-if="commentAuthorNotifyOn && commentAuthorNotifyHint" class="detail-line muted">{{ commentAuthorNotifyHint }}</p>
        <section v-if="itemCommentOn && detail.id" class="item-comments">
          <h4>{{ itemCommentTitle }}</h4>
          <div v-if="!isGuest" class="ic-compose">
            <el-input
              v-model="itemCommentDraft"
              type="textarea"
              :rows="2"
              maxlength="500"
              show-word-limit
              placeholder="写下你的评论…"
            />
            <el-checkbox
              v-if="followersOnlyCommentOn"
              v-model="itemCommentFollowersOnly"
              style="margin: 6px 0"
            >{{ browseLabels.followersOnlyCommentLabel || '仅粉丝可见' }}</el-checkbox>
            <el-button
              type="primary"
              size="small"
              :loading="itemCommentSubmitting"
              @click="submitItemComment"
            >{{ itemCommentSubmitLabel }}</el-button>
          </div>
          <div v-else class="muted">登录后可发表评论</div>
          <div v-if="itemCommentLoading" class="muted">加载中…</div>
          <div v-else-if="!itemComments.length" class="muted">{{ itemCommentEmpty }}</div>
          <article v-for="c in itemComments" :key="c.id" class="ic">
            <p class="ic-meta">
              <span>{{ c.nickname || c.username || '用户' }} · {{ c.createdAt }}</span>
              <el-button
                v-if="userFollowUiOn && c.username && !isGuest"
                link
                type="primary"
                size="small"
                @click="toggleFollowUser(c.username)"
              >{{ followBtnLabel(c.username) }}</el-button>
              <el-button
                v-if="commentReportOn && !isGuest"
                link
                type="danger"
                size="small"
                @click="openReport(c, 'comment')"
              >{{ browseLabels.commentReportLabel || '举报评论' }}</el-button>
            </p>
            <p>{{ c.body || '（无文字）' }}</p>
            <p v-if="c.followersOnly" class="muted">{{ browseLabels.followersOnlyCommentLabel || '仅粉丝可见' }}</p>
          </article>
        </section>
      </template>
    </el-drawer>

    <el-dialog v-model="reportVisible" :title="reportVerb" width="440px" destroy-on-close>
      <p class="apply-tip">举报「{{ reportTargetLabel }}」</p>
      <el-form label-position="top">
        <el-form-item v-if="reportReasonDictOn" :label="browseLabels.reportReasonLabel || '举报原因'" required>
          <el-select v-model="reportReasonCode" style="width: 100%" placeholder="请选择举报原因">
            <el-option
              v-for="opt in reportReasonOptions"
              :key="opt.value || opt"
              :label="opt.label || opt"
              :value="opt.label || opt.value || opt"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="reportReasonDictOn ? (browseLabels.reportReasonOtherPlaceholder || '补充说明（选填）') : '举报理由'">
          <el-input
            v-model="reportReason"
            type="textarea"
            :rows="4"
            maxlength="512"
            show-word-limit
            :placeholder="reportReasonDictOn ? (browseLabels.reportReasonOtherPlaceholder || '补充说明（选填）') : '请填写举报理由'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportVisible = false">取消</el-button>
        <el-button type="primary" :loading="reportSubmitting" @click="submitReport">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="applyVisible"
      :title="verbs.apply || '申请'"
      :width="richRemark ? '640px' : '440px'"
      destroy-on-close
    >
      <p class="apply-tip">对「{{ applyRow?.title }}」{{ verbs.apply || '提交申请' }}</p>
      <p v-if="scheduleText(applyRow)" class="apply-tip muted">{{ scheduleText(applyRow) }}</p>
      <p v-if="conflictHighlightOn && applyRow && wouldConflict(applyRow)" class="apply-tip conflict-tip">{{ conflictHighlightHint }}</p>
      <p v-if="conflictTip" class="apply-tip conflict-tip">{{ conflictTip }}</p>
      <el-form label-position="top">
        <el-form-item v-if="allowQty" :label="qtyLabel" required>
          <el-input-number
            v-model="applyQty"
            :min="1"
            :max="qtyMax"
            controls-position="right"
          />
          <span v-if="stockDisplay === 'count'" class="apply-tip muted" style="margin-left:8px">
            {{ stockCountLabel }} {{ applyRow?.stock ?? 0 }}
          </span>
        </el-form-item>
        <el-form-item v-if="pickLoanPeriod" :label="dueLabel" required>
          <el-date-picker
            v-model="applyDueAt"
            type="date"
            value-format="YYYY-MM-DD"
            :placeholder="`选择${dueLabel}`"
            :disabled-date="dueDisabledDate"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item v-if="collectAmount" :label="fineLabel" required>
          <el-input-number
            v-model="applyAmount"
            :min="0.01"
            :max="99999999"
            :precision="2"
            :step="10"
            controls-position="right"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item v-if="pickDateRange" label="起止日期" required>
          <el-date-picker
            v-model="applyPeriod"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始"
            end-placeholder="结束"
            :disabled-date="dueDisabledDate"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item v-if="isCrm" :label="channelLabel">
          <el-select v-model="applyChannel" style="width:100%" clearable :placeholder="channelPlaceholder">
            <el-option v-for="opt in channelOptions" :key="opt" :label="opt" :value="opt" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isCrm" :label="nextAtLabel">
          <el-date-picker
            v-model="applyNextFollow"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width:100%"
            placeholder="选填"
          />
        </el-form-item>
        <el-form-item v-if="teamSkillMatchOn" :label="teamSkillMatchLabel">
          <el-input
            v-model="mySkillTagsInput"
            :placeholder="skillTagsPlaceholder"
            maxlength="255"
          />
          <p v-if="skillMatchCount(applyRow) != null" class="muted" style="margin:4px 0 0">
            {{ teamSkillMatchLabel }}：重合 {{ skillMatchCount(applyRow) }} 项
            <span v-if="teamSkillMatchHint"> · {{ teamSkillMatchHint }}</span>
          </p>
          <p v-else class="muted" style="margin:4px 0 0">{{ teamSkillMatchEmpty }}</p>
        </el-form-item>
        <el-form-item v-if="datingMeetIntentOn" :label="meetIntentLabel" required>
          <el-select
            v-model="applyMeetIntent"
            style="width:100%"
            :placeholder="meetIntentPlaceholder"
          >
            <el-option v-for="opt in meetIntentOptions" :key="opt" :label="opt" :value="opt" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="rateOnApply" label="多维评分" required>
          <div class="rate-dims">
            <div v-for="d in ratingDims" :key="d.key" class="rate-dim-row">
              <span class="rate-dim-lab">{{ d.label }}</span>
              <el-rate v-model="applyDimScores[d.key]" :max="5" />
            </div>
          </div>
        </el-form-item>
        <el-form-item v-if="rateOnApply && allowAnonymousRating" label="匿名">
          <el-checkbox v-model="applyAnonymous">匿名提交</el-checkbox>
        </el-form-item>
        <el-form-item v-if="checkinOnApply" :label="checkinLabel" required>
          <el-input
            v-model="applyCheckinCode"
            maxlength="16"
            placeholder="向宿管/值班员索取签到码"
            @keyup.enter="submitApply"
          />
        </el-form-item>
        <el-form-item v-if="requireRemark && !richRemark" :label="remarkLabel" required>
          <el-input
            v-model="applyRemark"
            type="textarea"
            :rows="3"
            maxlength="255"
            :placeholder="`请填写${remarkLabel}`"
          />
        </el-form-item>
        <el-form-item v-if="richRemark" :label="ticket.label || '内容'" required>
          <RichTextEditor v-model="applyRemark" placeholder="请输入回复内容，可用工具栏排版；可 @昵称 引用" />
        </el-form-item>
        <el-form-item v-if="requireAttach" label="证明附件" required>
          <div class="attach-row">
            <el-upload
              :show-file-list="false"
              accept="image/*,.pdf,.doc,.docx"
              :http-request="onAttach"
            >
              <el-button size="small">{{ applyAttachUrl ? '重新上传' : '上传附件' }}</el-button>
            </el-upload>
            <a v-if="applyAttachUrl" :href="applyAttachUrl" target="_blank" rel="noopener noreferrer">已上传</a>
          </div>
        </el-form-item>
        <p v-if="requireMaterial && materialApplyHint" class="field-hint">{{ materialApplyHint }}</p>
        </el-form>
      <p v-if="!needApplyDialog" class="apply-tip muted">
        {{ autoApprove ? '确认后立即生效。' : '确认后提交，等待审核。' }}
      </p>
      <template #footer>
        <el-button @click="applyVisible = false">取消</el-button>
        <el-button type="primary" :loading="applyLoading" @click="submitApply">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="publishVisible" :title="publishDialogTitle" width="520px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item :label="fieldLabel('title', '名称')" required>
          <el-input
            v-model="publishTitle"
            maxlength="80"
            show-word-limit
            :placeholder="publishTitlePlaceholder"
          />
        </el-form-item>
        <el-form-item v-if="publishShowAuthor" :label="fieldLabel('author', '联系人')" required>
          <el-input
            v-model="publishAuthor"
            maxlength="64"
            :placeholder="`请填写${fieldLabel('author', '联系人')}`"
          />
        </el-form-item>
        <el-form-item :label="fieldLabel('category', '分类')" required>
          <el-select v-model="publishCategoryId" style="width:100%" :placeholder="`选择${fieldLabel('category', '分类')}`">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="publishShowStock" :label="fieldLabel('stock', '余座')" required>
          <el-input-number v-model="publishStock" :min="1" :max="99" controls-position="right" />
        </el-form-item>
        <el-form-item v-if="publishShowStartAt" :label="fieldLabel('startAt', '出发时间')" required>
          <el-date-picker
            v-model="publishStartAt"
            type="datetime"
            value-format="YYYY-MM-DD HH:mm:ss"
            format="YYYY-MM-DD HH:mm"
            style="width:100%"
            :placeholder="`请选择${fieldLabel('startAt', '出发时间')}`"
          />
        </el-form-item>
        <template v-if="carpoolCampusDictOn">
          <el-form-item :label="carpoolCampusStartLabel" required>
            <el-select
              v-model="publishStartCampus"
              filterable
              clearable
              :placeholder="carpoolCampusPlaceholder"
              style="width:100%"
            >
              <el-option v-for="c in carpoolCampusOptions" :key="'ps' + c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
          <el-form-item :label="carpoolCampusEndLabel" required>
            <el-select
              v-model="publishEndCampus"
              filterable
              clearable
              :placeholder="carpoolCampusPlaceholder"
              style="width:100%"
            >
              <el-option v-for="c in carpoolCampusOptions" :key="'pe' + c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item v-if="carpoolViaPointsOn" :label="carpoolViaPointsLabel">
          <el-input
            v-model="publishViaPoints"
            type="textarea"
            :rows="2"
            :placeholder="carpoolViaPointsPlaceholder"
          />
        </el-form-item>
        <el-form-item v-if="carpoolShareNoteOn" :label="carpoolShareNoteLabel">
          <el-input
            v-model="publishShareNote"
            type="textarea"
            :rows="2"
            :placeholder="carpoolShareNotePlaceholder"
          />
        </el-form-item>
        <el-form-item v-if="carpoolPrefNoteOn" :label="carpoolPrefNoteLabel">
          <el-input v-model="publishPrefNote" :placeholder="carpoolPrefNotePlaceholder" />
        </el-form-item>
        <el-form-item v-if="carpoolLuggageOn" :label="carpoolLuggageCountLabel">
          <el-input-number v-model="publishLuggageCount" :min="0" :max="99" controls-position="right" />
        </el-form-item>
        <el-form-item v-if="carpoolAaCalcOn" :label="fareTotalLabel">
          <el-input-number
            v-model="publishFareTotalYuan"
            :min="0"
            :max="99999"
            :precision="2"
            controls-position="right"
          />
          <p v-if="fareTotalHint" class="apply-tip muted">{{ fareTotalHint }}</p>
        </el-form-item>
        <el-form-item v-if="carpoolDepartRemindOn" :label="carpoolDepartRemindLeadLabel">
          <el-input-number
            v-model="publishRemindBeforeMinutes"
            :min="0"
            :max="1440"
            controls-position="right"
          />
          <p v-if="carpoolDepartRemindHint" class="apply-tip muted">{{ carpoolDepartRemindHint }}</p>
        </el-form-item>
        <el-form-item :label="fieldLabel('isbn', publishUsesRichBody ? '正文' : '备注')" required>
          <RichTextEditor
            v-if="publishUsesRichBody"
            v-model="publishBody"
            placeholder="请输入正文，可用工具栏排版"
          />
          <el-input
            v-else
            v-model="publishBody"
            type="textarea"
            :rows="3"
            maxlength="255"
            show-word-limit
            :placeholder="publishIsbnPlaceholder"
          />
        </el-form-item>
        <el-form-item v-if="originKindOn" :label="originKindLabel">
          <el-radio-group v-model="publishOriginKind">
            <el-radio value="original">{{ originOriginalLabel }}</el-radio>
            <el-radio value="reprint">{{ originReprintLabel }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="accessPasswordOn" :label="accessPasswordLabel">
          <el-input v-model="publishAccessPassword" maxlength="64" show-password :placeholder="accessPasswordHint || '选填'" />
        </el-form-item>
      </el-form>
      <p class="apply-tip muted">{{ publishTip }}</p>
      <p v-if="draftBoxOn && dailyPostLimitHint" class="apply-tip muted">{{ dailyPostLimitHint }}</p>
      <p v-if="draftAutoSaveOn" class="apply-tip muted">{{ draftAutoSaveHint }}</p>
      <p v-if="draftAutoSaveOn && draftAutoSavedAt" class="apply-tip muted">{{ draftAutoSavedLabel }} · {{ draftAutoSavedAt }}</p>
      <p v-if="sensitiveWordHint" class="apply-tip muted">{{ sensitiveWordHint }}</p>
      <template #footer>
        <el-button @click="publishVisible = false">取消</el-button>
        <el-button
          v-if="draftBoxOn"
          :loading="publishLoading"
          @click="submitPublish(true)"
        >{{ saveDraftLabel }}</el-button>
        <el-button type="primary" :loading="publishLoading" @click="submitPublish(false)">{{ publishSubmitLabel }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup src="./ArchiveBrowse.setup.js"></script>

<style scoped src="./ArchiveBrowse.css"></style>
