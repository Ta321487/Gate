"""DOM-SHOP 零售软皮登记表：扫词/分类/文案/SKU/多店店名一处维护。

新皮只加一条 ``RetailNichePack`` + 测试行；禁止在 builders 再写 ``niche ==``。
开题平台名（如「方木」）不得写入 ``mp_shops``。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


SkuRow = tuple[str, str, str, int, str]  # title, price, sku, cat_id, seller_note


@dataclass(frozen=True)
class MpShop:
    name: str
    intro: str


@dataclass(frozen=True)
class RetailNichePack:
    id: str
    hints: tuple[str, ...]
    categories: tuple[str, str, str]
    eyebrow: str
    lead: str
    notice_title: str
    notice_body: str
    title_lab: str
    sku_lab: str
    note_lab: str
    arch_lab: str
    arch_menu: str
    arch_browse: str
    admin_name: str
    sub_name: str
    admin_lab: str
    skus: tuple[SkuRow, ...]
    mp_shops: tuple[MpShop, MpShop]
    mp_eyebrow: str
    mp_lead: str
    cat_menu_lab: str
    mp_notice_title: str
    mp_notice_body: str
    mp_promo_title: str
    mp_promo_body: str
    flags: frozenset[str] = field(default_factory=frozenset)
    # 详情属性适用表：key→分类名子串（命中任一才在管理端/买家露）。
    # 未出现在表中的 detailAttrKeys 视为 always；空表=不裁剪（整池选填）。
    detail_attr_when: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def gift_line_custom(self) -> bool:
        return "gift_line_custom" in self.flags


def _sku(
    title: str, price: str, sku: str, cat_id: int, note: str = ""
) -> SkuRow:
    return (title, price, sku, cat_id, note)


_PACKS: tuple[RetailNichePack, ...] = (
    RetailNichePack(
        id="pharmacy",
        hints=("药店", "药品", "药房", "医药"),
        categories=("药品", "保健", "护理"),
        eyebrow="药店选购",
        lead="验证码登录；浏览药品保健护理，加入购物车并提交订单。",
        notice_title="药店选购须知",
        notice_body="分类商品上架，下单后由管理员确认发货或自提。",
        title_lab="商品名",
        sku_lab="国药准字/货号",
        note_lab="用药说明",
        arch_lab="商品",
        arch_menu="商品管理",
        arch_browse="商品浏览",
        admin_name="商城主管",
        sub_name="订单管理员",
        admin_lab="商城主管（总管）",
        skus=(
            _sku("常用感冒药套装", "39.90", "PH-01", 1, "常见感冒症状备用"),
            _sku("维生素 C 片", "29.90", "PH-02", 2, "日常补充"),
            _sku("免洗手消毒液", "19.90", "PH-03", 3, "随身护理"),
            _sku("创可贴家庭装", "15.00", "PH-04", 3, "小伤口护理"),
        ),
        mp_shops=(
            MpShop("康宁大药房", "常备药与保健"),
            MpShop("安心护理店", "护理与消毒用品"),
        ),
        mp_eyebrow="多商家商城",
        mp_lead="买家选购下单，商家入驻开店，平台统一监管；平台管理员为系统预制账号，不开放自助注册。",
        cat_menu_lab="商品分类",
        mp_notice_title="商城开业",
        mp_notice_body="多店入驻；下单后可在订单页查看进度。",
        mp_promo_title="换季感冒药促销",
        mp_promo_body="感冒药套装满 2 件减 5 元（待平台审核）。",
    ),
    RetailNichePack(
        id="pet",
        hints=("宠物用品", "宠粮", "猫粮", "狗粮"),
        categories=("主粮", "零食", "洗护"),
        eyebrow="宠物用品",
        lead="验证码登录；浏览主粮零食洗护，加入购物车并提交订单。",
        notice_title="宠物用品须知",
        notice_body="分类商品上架，下单后由管理员确认发货或自提。",
        title_lab="商品名",
        sku_lab="规格货号",
        note_lab="适用说明",
        arch_lab="商品",
        arch_menu="商品管理",
        arch_browse="商品浏览",
        admin_name="商城主管",
        sub_name="订单管理员",
        admin_lab="商城主管（总管）",
        skus=(
            _sku("成猫粮 1.5kg", "68.00", "PT-01", 1, "适口配方"),
            _sku("狗零食肉干", "28.00", "PT-02", 2, "训练奖励"),
            _sku("宠物沐浴露", "35.00", "PT-03", 3, "温和洗护"),
            _sku("猫砂 5L", "32.00", "PT-04", 3, "结团除臭"),
        ),
        mp_shops=(
            MpShop("喵汪主粮店", "主粮与零食"),
            MpShop("毛孩洗护店", "洗护与日用"),
        ),
        mp_eyebrow="多商家商城",
        mp_lead="买家选购下单，商家入驻开店，平台统一监管；平台管理员为系统预制账号，不开放自助注册。",
        cat_menu_lab="商品分类",
        mp_notice_title="商城开业",
        mp_notice_body="多店入驻；下单后可在订单页查看进度。",
        mp_promo_title="主粮满减周",
        mp_promo_body="成猫粮满 2 袋减 10 元（待平台审核）。",
    ),
    RetailNichePack(
        id="auto",
        hints=("汽配", "汽车配件", "车品"),
        categories=("保养件", "车饰", "工具"),
        eyebrow="汽配商城",
        lead="验证码登录；浏览保养件车饰工具，加入购物车并提交订单。",
        notice_title="汽配选购须知",
        notice_body="分类商品上架，下单后由管理员确认发货或自提。",
        title_lab="商品名",
        sku_lab="配件号",
        note_lab="适配车型",
        arch_lab="商品",
        arch_menu="商品管理",
        arch_browse="商品浏览",
        admin_name="商城主管",
        sub_name="订单管理员",
        admin_lab="商城主管（总管）",
        skus=(
            _sku("机油 4L 套装", "128.00", "AU-01", 1, "常规保养"),
            _sku("车载香薰", "39.00", "AU-02", 2, "车内清新"),
            _sku("随车工具包", "59.00", "AU-03", 3, "应急维修"),
            _sku("雨刷片一对", "45.00", "AU-04", 1, "通用接口"),
        ),
        mp_shops=(
            MpShop("车管家保养店", "机油与保养件"),
            MpShop("车饰工具店", "车饰与工具"),
        ),
        mp_eyebrow="多商家商城",
        mp_lead="买家选购下单，商家入驻开店，平台统一监管；平台管理员为系统预制账号，不开放自助注册。",
        cat_menu_lab="商品分类",
        mp_notice_title="商城开业",
        mp_notice_body="多店入驻；下单后可在订单页查看进度。",
        mp_promo_title="保养件折扣",
        mp_promo_body="机油套装限时优惠（待平台审核）。",
    ),
    RetailNichePack(
        id="beauty",
        hints=("化妆品", "美妆", "护肤"),
        categories=("护肤", "彩妆", "个护"),
        eyebrow="美妆选购",
        lead="验证码登录；浏览护肤彩妆个护，加入购物车并提交订单。",
        notice_title="美妆选购须知",
        notice_body="分类商品上架，下单后由管理员确认发货或自提。",
        title_lab="商品名",
        sku_lab="规格",
        note_lab="功效说明",
        arch_lab="商品",
        arch_menu="商品管理",
        arch_browse="商品浏览",
        admin_name="商城主管",
        sub_name="订单管理员",
        admin_lab="商城主管（总管）",
        skus=(
            _sku("保湿面霜 50g", "89.00", "BE-01", 1, "日常保湿"),
            _sku("口红试色装", "59.00", "BE-02", 2, "多色试色"),
            _sku("氨基酸洗面奶", "49.00", "BE-03", 3, "温和清洁"),
            _sku("面膜 5 片装", "39.00", "BE-04", 1, "补水护理"),
        ),
        mp_shops=(
            MpShop("水润护肤店", "护肤与面膜"),
            MpShop("彩妆个护店", "彩妆与个护"),
        ),
        mp_eyebrow="多商家商城",
        mp_lead="买家选购下单，商家入驻开店，平台统一监管；平台管理员为系统预制账号，不开放自助注册。",
        cat_menu_lab="商品分类",
        mp_notice_title="商城开业",
        mp_notice_body="多店入驻；下单后可在订单页查看进度。",
        mp_promo_title="护肤节满减",
        mp_promo_body="面霜满减活动（待平台审核）。",
    ),
    RetailNichePack(
        id="market",
        hints=("超市", "便利店"),
        categories=("食品", "百货", "零食"),
        eyebrow="超市选购",
        lead="验证码登录；浏览食品百货零食，加入购物车并提交订单。",
        notice_title="超市选购须知",
        notice_body="分类商品上架，下单后由管理员确认发货或自提。",
        title_lab="商品名",
        sku_lab="货号",
        note_lab="商品说明",
        arch_lab="商品",
        arch_menu="商品管理",
        arch_browse="商品浏览",
        admin_name="商城主管",
        sub_name="订单管理员",
        admin_lab="商城主管（总管）",
        skus=(
            _sku("牛奶 12 盒装", "56.00", "MK-01", 1, "常温保存"),
            _sku("抽纸 24 包", "39.90", "MK-02", 2, "家庭装"),
            _sku("坚果礼盒", "68.00", "MK-03", 3, "混合坚果"),
            _sku("方便面箱装", "45.00", "MK-04", 1, "整箱囤货"),
        ),
        mp_shops=(
            MpShop("邻里食品店", "牛奶与方便面"),
            MpShop("百货零食店", "百货与零食"),
        ),
        mp_eyebrow="多商家商城",
        mp_lead="买家选购下单，商家入驻开店，平台统一监管；平台管理员为系统预制账号，不开放自助注册。",
        cat_menu_lab="商品分类",
        mp_notice_title="商城开业",
        mp_notice_body="多店入驻；下单后可在订单页查看进度。",
        mp_promo_title="周末食品促销",
        mp_promo_body="牛奶箱装满减（待平台审核）。",
    ),
    # 须排在 office 前：开题常写「手办、文具、服饰」，裸「文具」会把周边题洗成办公皮
    RetailNichePack(
        id="anime",
        # 勿写开题品牌名（柚子/方木/超新…）；题名「…动漫周边…」靠品类词命中
        hints=(
            "动漫周边",
            "二次元周边",
            "动漫衍生品",
            "手办",
            "谷子",
            "立牌",
            "徽章",
            "吧唧",
        ),
        categories=("手办模型", "文具谷子", "服饰配件"),
        eyebrow="动漫周边选购",
        lead="验证码登录；浏览手办、文具谷子与服饰配件，加入购物车并提交订单。",
        notice_title="周边选购须知",
        notice_body="手办与谷子分类上架，下单后由店家确认发货或自提。",
        title_lab="周边名称",
        sku_lab="货号",
        note_lab="系列说明",
        arch_lab="周边商品",
        arch_menu="周边管理",
        arch_browse="周边浏览",
        admin_name="周边商城主管",
        sub_name="订单管理员",
        admin_lab="周边商城主管（总管）",
        skus=(
            _sku("角色手办 1/7", "189.00", "AN-01", 1, "景品级，盒装"),
            _sku("亚克力立牌", "39.00", "AN-02", 2, "桌面摆件"),
            _sku("金属徽章套装", "29.00", "AN-03", 2, "三枚装"),
            _sku("同人帆布袋", "45.00", "AN-04", 3, "日常通勤"),
        ),
        mp_shops=(
            MpShop("手办专营店", "手办与模型"),
            MpShop("谷子文具店", "立牌徽章与文具谷子"),
        ),
        mp_eyebrow="多商家周边商城",
        mp_lead=(
            "买家选购动漫周边，商家入驻开店，平台统一监管；"
            "平台管理员为系统预制账号，不开放自助注册。"
        ),
        cat_menu_lab="周边分类",
        mp_notice_title="周边选购须知",
        mp_notice_body="多店周边入驻；下单后可在订单页查看进度。",
        mp_promo_title="手办谷子周",
        mp_promo_body="立牌满 2 件减 5 元（待平台审核）。",
    ),
    RetailNichePack(
        id="office",
        # 不用裸「文具」：会与动漫周边开题「手办、文具、服饰」串皮
        hints=("办公用品", "办公文具", "复印纸"),
        categories=("文具", "耗材", "桌面"),
        eyebrow="办公文具",
        lead="验证码登录；浏览文具耗材，加入购物车并提交订单。",
        notice_title="办公选购须知",
        notice_body="分类商品上架，下单后由管理员确认发货或自提。",
        title_lab="商品名",
        sku_lab="货号",
        note_lab="规格说明",
        arch_lab="商品",
        arch_menu="商品管理",
        arch_browse="商品浏览",
        admin_name="商城主管",
        sub_name="订单管理员",
        admin_lab="商城主管（总管）",
        skus=(
            _sku("中性笔 12 支装", "19.90", "OF-01", 1, "办公常用"),
            _sku("A4 复印纸 500 张", "28.00", "OF-02", 2, "打印耗材"),
            _sku("桌面收纳盒", "35.00", "OF-03", 3, "桌面整理"),
            _sku("订书机套装", "25.00", "OF-04", 1, "含钉书针"),
        ),
        mp_shops=(
            MpShop("文具优选店", "笔与订书机"),
            MpShop("耗材桌面店", "纸张与收纳"),
        ),
        mp_eyebrow="多商家商城",
        mp_lead="买家选购下单，商家入驻开店，平台统一监管；平台管理员为系统预制账号，不开放自助注册。",
        cat_menu_lab="商品分类",
        mp_notice_title="商城开业",
        mp_notice_body="多店入驻；下单后可在订单页查看进度。",
        mp_promo_title="开学文具周",
        mp_promo_body="中性笔套装满减（待平台审核）。",
    ),
    RetailNichePack(
        id="agri",
        hints=("农资",),
        categories=("肥料", "农药", "农机件"),
        eyebrow="农资选购",
        lead="验证码登录；浏览肥料农药农机件，加入购物车并提交订单。",
        notice_title="农资选购须知",
        notice_body="分类商品上架，下单后由管理员确认发货或自提。",
        title_lab="商品名",
        sku_lab="规格含量",
        note_lab="施用说明",
        arch_lab="商品",
        arch_menu="商品管理",
        arch_browse="商品浏览",
        admin_name="商城主管",
        sub_name="订单管理员",
        admin_lab="商城主管（总管）",
        skus=(
            _sku("复合肥 5kg", "48.00", "AG-01", 1, "大田追肥"),
            _sku("园艺喷雾壶", "29.00", "AG-02", 2, "喷施工具"),
            _sku("农用手套", "18.00", "AG-03", 3, "作业防护"),
            _sku("种子套装", "22.00", "AG-04", 1, "时令菜种"),
        ),
        mp_shops=(
            MpShop("田园肥料店", "肥料与种子"),
            MpShop("农机配件店", "喷壶与手套"),
        ),
        mp_eyebrow="多商家商城",
        mp_lead="买家选购下单，商家入驻开店，平台统一监管；平台管理员为系统预制账号，不开放自助注册。",
        cat_menu_lab="商品分类",
        mp_notice_title="商城开业",
        mp_notice_body="多店入驻；下单后可在订单页查看进度。",
        mp_promo_title="春耕肥料促销",
        mp_promo_body="复合肥满减（待平台审核）。",
    ),
    RetailNichePack(
        id="gift",
        hints=("定制礼品", "礼品定制", "刻字"),
        categories=("杯壶刻字", "服饰印制", "相册抱枕"),
        eyebrow="定制礼品",
        lead="验证码登录；选择礼品，填写刻字或上传图片后下单，制作完成再发货。",
        notice_title="定制须知",
        notice_body="下单请填写刻字、字体颜色尺寸，并可上传图片。提交后进入待制作，制作完成再发货。",
        title_lab="礼品名称",
        sku_lab="货号",
        note_lab="可定制说明",
        arch_lab="礼品",
        arch_menu="礼品管理",
        arch_browse="礼品浏览",
        admin_name="礼品店主管",
        sub_name="制作员",
        admin_lab="礼品店主管（总管）",
        skus=(
            _sku("刻字马克杯", "39.00", "GF-01", 1, "可刻字"),
            _sku("定制T恤", "69.00", "GF-02", 2, "可印图"),
            _sku("定制相册", "88.00", "GF-03", 3, "可上传照片"),
            _sku("定制抱枕", "59.00", "GF-04", 3, "可印图案"),
        ),
        mp_shops=(
            MpShop("刻字杯壶店", "杯壶刻字"),
            MpShop("印制定制店", "服饰与抱枕"),
        ),
        mp_eyebrow="多商家商城",
        mp_lead="买家选购下单，商家入驻开店，平台统一监管；平台管理员为系统预制账号，不开放自助注册。",
        cat_menu_lab="商品分类",
        mp_notice_title="商城开业",
        mp_notice_body="多店入驻；下单后可在订单页查看进度。",
        mp_promo_title="定制礼品周",
        mp_promo_body="马克杯刻字满减（待平台审核）。",
        flags=frozenset({"gift_line_custom"}),
    ),
    RetailNichePack(
        id="fitness",
        hints=(
            "健身用品",
            "健身器材",
            "运动用品",
            "哑铃",
            "杠铃",
            "瑜伽垫",
            "弹力带",
        ),
        categories=("增肌训练", "减脂塑形", "护具康复"),
        eyebrow="健身用品",
        lead="验证码登录；浏览增肌减脂与护具器材，加入购物车并提交订单。",
        notice_title="健身选购须知",
        notice_body="器械与护具分类上架，下单后由商家确认发货或自提。",
        title_lab="健身用品名称",
        sku_lab="规格型号",
        note_lab="适用说明",
        arch_lab="健身用品",
        arch_menu="健身用品管理",
        arch_browse="健身用品浏览",
        admin_name="健身商城主管",
        sub_name="订单管理员",
        admin_lab="健身商城主管（总管）",
        skus=(
            _sku("六角哑铃 10kg 一对", "129.00", "FT-DB10", 1, "铸铁包胶，适合家用增肌。"),
            _sku("奥杆杠铃套装 20kg", "289.00", "FT-BB20", 1, "含卡扣与配重片。"),
            _sku("瑜伽垫 10mm 防滑", "69.00", "FT-YG10", 2, "TPE 材质，适合减脂塑形跟练。"),
            _sku("弹力带阻力套装", "49.00", "FT-RB01", 2, "多档阻力，便于拉伸塑形。"),
            _sku("护腕护膝组合", "39.00", "FT-GD01", 3, "加压透气，康复训练可用。"),
        ),
        mp_shops=(
            MpShop("力量器材店", "哑铃杠铃与增肌器材"),
            MpShop("塑形家居店", "瑜伽垫弹力带与护具"),
        ),
        mp_eyebrow="多商家健身商城",
        mp_lead=(
            "买家选购健身用品，商家入驻开店，平台统一监管；"
            "平台管理员为系统预制账号，不开放自助注册。"
        ),
        cat_menu_lab="健身用品分类",
        mp_notice_title="健身选购须知",
        mp_notice_body="多店健身用品入驻；下单后可在订单页查看进度。",
        mp_promo_title="春季哑铃满减",
        mp_promo_body="六角哑铃满 2 件减 20 元（待平台审核）。",
        # 器材类型维取值；开题不明写适用矩阵时靠此皮默认（禁 NLP 猜开题）
        detail_attr_when={
            "loadCap": ("哑铃", "杠铃", "壶铃"),
            "resistance": ("弹力带", "拉力"),
        },
    ),
    RetailNichePack(
        id="sports",
        hints=(
            "体育用品",
            "体育商城",
            "球类用品",
            "运动装备",
            "球拍",
            "跑鞋",
            "运动服",
        ),
        categories=("球类器材", "鞋服", "护具配件"),
        eyebrow="体育用品",
        lead="验证码登录；浏览球类器材与鞋服护具，加入购物车并提交订单。",
        notice_title="体育选购须知",
        notice_body="球类、鞋服与护具分类上架，下单后由商家确认发货或自提。",
        title_lab="体育用品名称",
        sku_lab="规格货号",
        note_lab="适用说明",
        arch_lab="体育用品",
        arch_menu="体育用品管理",
        arch_browse="体育用品浏览",
        admin_name="体育商城主管",
        sub_name="订单管理员",
        admin_lab="体育商城主管（总管）",
        skus=(
            _sku("7 号篮球", "89.00", "SP-BB07", 1, "室内外通用，适合训练比赛。"),
            _sku("羽毛球拍双拍套装", "129.00", "SP-BD01", 1, "含球与拍套，入门级。"),
            _sku("跑步鞋 透气款", "199.00", "SP-RN01", 2, "缓震透气，日常跑步。"),
            _sku("速干运动短袖", "59.00", "SP-TS01", 2, "排汗速干，训练穿着。"),
            _sku("护膝护腕组合", "45.00", "SP-GD01", 3, "加压透气，运动防护。"),
        ),
        mp_shops=(
            MpShop("球类器材店", "篮球羽毛球等球类"),
            MpShop("鞋服护具店", "跑鞋运动服与护具"),
        ),
        mp_eyebrow="多商家体育商城",
        mp_lead=(
            "买家选购体育用品，商家入驻开店，平台统一监管；"
            "平台管理员为系统预制账号，不开放自助注册。"
        ),
        cat_menu_lab="体育用品分类",
        mp_notice_title="体育选购须知",
        mp_notice_body="多店体育用品入驻；下单后可在订单页查看进度。",
        mp_promo_title="球类开学期满减",
        mp_promo_body="7 号篮球满 2 个减 15 元（待平台审核）。",
    ),
)

_BY_ID: dict[str, RetailNichePack] = {p.id: p for p in _PACKS}


def all_retail_niche_packs() -> tuple[RetailNichePack, ...]:
    return _PACKS


def iter_retail_niche_packs() -> Iterator[RetailNichePack]:
    yield from _PACKS


def get_retail_niche(niche_id: str | None) -> RetailNichePack | None:
    if not niche_id:
        return None
    return _BY_ID.get(niche_id)


def shop_retail_niche_rules() -> list[tuple[tuple[str, ...], str, tuple[str, str, str]]]:
    """兼容 ``scene_scan.SHOP_RETAIL_NICHE_RULES`` 形状。"""
    return [(p.hints, p.id, p.categories) for p in _PACKS]


def niche_skus_map() -> dict[str, list[tuple[str, str, str, int]]]:
    """兼容旧 ``_SHOP_RETAIL_NICHE_SKUS``（无 note）。"""
    out: dict[str, list[tuple[str, str, str, int]]] = {}
    for p in _PACKS:
        out[p.id] = [(t, pr, s, c) for t, pr, s, c, _n in p.skus]
    return out
