<template>
  <div class="home" :data-home="homeStyle">
    <!-- 商城货架：分类栏 + Banner + 新品 -->
    <template v-if="homeStyle === 'mall'">
      <div class="mall">
        <section class="mall-hero" aria-label="分类与推荐">
          <aside class="mall-cats" aria-label="商品分类">
            <button
              v-for="c in mallCategories"
              :key="c.id"
              type="button"
              class="mall-cat"
              @click="goCategory(c)"
            >
              {{ c.name }}
            </button>
            <p v-if="!mallCategories.length" class="mall-cat-empty">暂无分类</p>
          </aside>
          <div class="mall-banner" aria-roledescription="carousel" aria-label="首页推荐">
            <button
              type="button"
              class="mall-banner-slide"
              :aria-label="mallBannerTitle"
              :style="mallBannerStyle"
              @click="onMallBanner"
            >
              <div v-if="!mallBannerSrc" class="mall-banner-fallback">
                <p class="mall-banner-kicker">{{ mallBannerTitle }}</p>
                <p class="mall-banner-lead">{{ mallBannerLead }}</p>
              </div>
            </button>
            <div v-if="mallSlides.length > 1" class="mall-dots">
              <button
                v-for="(s, i) in mallSlides"
                :key="'bd' + i"
                type="button"
                :class="{ on: i === mallIndex }"
                :aria-label="'第' + (i + 1) + '张'"
                @click="showMallSlide(i)"
              />
            </div>
          </div>
        </section>

        <section class="mall-new" aria-label="新品上架">
          <div class="mall-new-hd">
            <h2 class="mall-new-title">新品上架</h2>
            <button type="button" class="more" @click="goArchive">查看更多 &gt;&gt;</button>
          </div>
          <div class="mall-grid">
            <button
              v-for="item in mallProducts"
              :key="item.id"
              type="button"
              class="mall-card"
              @click="goProduct(item)"
            >
              <div
                class="mall-cover"
                :style="item.cover ? { backgroundImage: `url('${item.cover}')` } : undefined"
              >
                <span v-if="!item.cover" class="mall-cover-letter">{{ item.letter }}</span>
              </div>
              <div class="mall-copy">
                <h3>{{ item.title }}</h3>
                <p>{{ item.lead }}</p>
                <div class="mall-foot">
                  <span class="mall-price">{{ item.price }}</span>
                  <span class="mall-meta">{{ item.salesText || (item.shop ? item.shop : item.meta) }}</span>
                </div>
              </div>
            </button>
          </div>
          <div v-if="!mallProducts.length" class="mall-empty">
            <EmptyHint
              title="暂无商品"
              desc="货架还空着，去逛逛全部目录吧。"
              mark="购"
              cta-label="去逛逛"
              @cta="goArchive"
            />
          </div>
        </section>

        <section v-if="mallHot.length" class="mall-new" aria-label="热销商品">
          <div class="mall-new-hd">
            <h2 class="mall-new-title">热销商品</h2>
            <button type="button" class="more" @click="goArchive">查看更多 &gt;&gt;</button>
          </div>
          <div class="mall-grid">
            <button
              v-for="item in mallHot"
              :key="'hot-' + item.id"
              type="button"
              class="mall-card"
              @click="goProduct(item)"
            >
              <div
                class="mall-cover"
                :style="item.cover ? { backgroundImage: `url('${item.cover}')` } : undefined"
              >
                <span v-if="!item.cover" class="mall-cover-letter">{{ item.letter }}</span>
              </div>
              <div class="mall-copy">
                <h3>{{ item.title }}</h3>
                <p>{{ item.lead }}</p>
                <div class="mall-foot">
                  <span class="mall-price">{{ item.price }}</span>
                  <span class="mall-meta">{{ item.salesText || (item.shop ? item.shop : item.meta) }}</span>
                </div>
              </div>
            </button>
          </div>
        </section>

        <!-- 挂 flash_price 且有窗内活动价才出；点进详情按下单活动价走 -->
        <section v-if="flashOn && mallFlashProducts.length" class="mall-flash" aria-label="限时特价">
          <div class="mall-new-hd">
            <h2 class="mall-new-title">{{ mallFlashTitle }}</h2>
            <button type="button" class="more" @click="goArchive">{{ mallFlashMore }} &gt;&gt;</button>
          </div>
          <div class="mall-grid">
            <button
              v-for="item in mallFlashProducts"
              :key="'flash-' + item.id"
              type="button"
              class="mall-card"
              @click="goProduct(item)"
            >
              <div
                class="mall-cover"
                :style="item.cover ? { backgroundImage: `url('${item.cover}')` } : undefined"
              >
                <span class="mall-flash-badge">{{ flashBadge }}</span>
                <span v-if="!item.cover" class="mall-cover-letter">{{ item.letter }}</span>
              </div>
              <div class="mall-copy">
                <h3>{{ item.title }}</h3>
                <p v-if="item.countdown" class="mall-flash-cd">{{ item.countdown }}</p>
                <p v-else>{{ item.lead }}</p>
                <div class="mall-foot">
                  <span class="mall-price">
                    {{ item.price }}
                    <span v-if="item.listPrice" class="mall-list-price">{{ item.listPrice }}</span>
                  </span>
                  <span class="mall-meta">{{ item.shop ? item.shop : item.meta }}</span>
                </div>
              </div>
            </button>
          </div>
        </section>
      </div>
    </template>

    <!-- 默认首页：品牌首屏 + 主行动 + 短链轨（禁止功能方卡墙） -->
    <template v-else-if="homeStyle !== 'editorial'">
      <section class="cards-hero" aria-label="门户首屏">
        <div class="cards-hero-panel">
          <p class="cards-kicker">{{ appName }}</p>
          <h1>{{ cardsHeroTitle }}</h1>
          <p class="cards-lead">{{ lead }}</p>
          <p v-if="industrySkinHint" class="skin-hint">{{ industrySkinHint }}</p>
          <div class="cards-cta-row">
            <button
              v-if="primaryHomeCard"
              type="button"
              class="cards-cta"
              @click="go(primaryHomeCard)"
            >{{ primaryHomeCard.label }}</button>
            <button
              v-if="secondaryHomeCard"
              type="button"
              class="cards-cta ghost"
              @click="go(secondaryHomeCard)"
            >{{ secondaryHomeCard.label }}</button>
          </div>
        </div>
      </section>
      <nav v-if="railHomeCards.length" class="cards-rail" aria-label="更多入口">
        <button
          v-for="card in railHomeCards"
          :key="card.to"
          type="button"
          class="cards-rail-btn"
          @click="go(card)"
        >{{ card.label }}</button>
      </nav>
    </template>

    <!-- 资讯 + 侧栏（内容域） -->
    <template v-else>
      <div class="editorial">
        <section class="news" aria-label="资讯动态">
          <div class="news-hd">
            <div>
              <p class="news-kicker">{{ newsKicker }}</p>
              <h2 class="news-title">{{ newsTitle }}</h2>
            </div>
            <button type="button" class="more" @click="goNotices">+ 查看更多</button>
          </div>
          <div class="news-track">
            <button
              v-for="(item, i) in newsItems"
              :key="item.id || i"
              type="button"
              class="news-card"
              @click="openNews(item)"
            >
              <div
                class="news-cover"
                :style="item.cover ? { backgroundImage: `url('${item.cover}')` } : undefined"
              />
              <div class="news-copy">
                <h3>{{ item.title }}</h3>
                <p>{{ item.lead }}</p>
              </div>
            </button>
            <div v-if="!newsItems.length" class="news-empty">
              <EmptyHint
                title="暂无资讯"
                desc="可先浏览目录或公告。"
                mark="讯"
                cta-label="去逛逛"
                @cta="goArchive"
              />
            </div>
          </div>
          <div class="quick" aria-label="快捷入口">
            <button
              v-for="card in quickCards"
              :key="card.to"
              type="button"
              class="quick-btn"
              @click="go(card)"
            >
              {{ card.label }}
            </button>
          </div>
        </section>

        <aside class="claim" aria-label="门户主张">
          <div
            class="claim-photo"
            :style="claimCover ? { backgroundImage: `url('${claimCover}')` } : undefined"
          />
          <div class="claim-box">
            <p class="claim-text">{{ claimText }}</p>
          </div>
        </aside>
      </div>
    </template>

    <p v-if="!loggedIn && guestBrowse" class="hint">
      部分内容需登录后使用 ·
      <router-link :to="{ path: '/login', query: { redirect: '/home' } }">去登录</router-link>
    </p>
  </div>
</template>

<script setup src="./PortalHome.setup.js"></script>

<style scoped src="./PortalHome.css"></style>
