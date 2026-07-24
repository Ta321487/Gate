"""各领域档案字段映射（注册/个人资料）。"""

from __future__ import annotations

import copy
from typing import Any


def _pf(
    key: str,
    label: str,
    *,
    storage: str = "json",
    required: bool = False,
    on_register: bool = False,
    max_length: int = 64,
    placeholder: str = "",
    field_type: str = "string",
    options: list[str] | None = None,
    format: str = "",
    required_when: dict[str, Any] | None = None,
    visible_when: dict[str, Any] | None = None,
) -> dict[str, Any]:
    f: dict[str, Any] = {
        "key": key,
        "label": label,
        "storage": storage,
        "type": field_type,
        "required": required,
        "onRegister": on_register,
        "maxLength": max_length,
    }
    if placeholder:
        f["placeholder"] = placeholder
    if options:
        f["options"] = options
    if format:
        f["format"] = format
    if required_when:
        f["requiredWhen"] = required_when
    if visible_when:
        f["visibleWhen"] = visible_when
    return f


def _when(field: str, values: list[str]) -> dict[str, Any]:
    """条件必填/可见：extras[field] 落在 values 内时生效。"""
    return {"field": field, "in": list(values)}


_CAMPUS_ID = _when("identityType", ["学生", "教职工"])
_LIBRARY_CAMPUS = _when("readerType", ["本科生", "研究生", "教职工"])
_LIBRARY_STUDENT = _when("readerType", ["本科生", "研究生"])
_IT_CAMPUS = _when("identityType", ["学生", "教职工"])
_OFF_CAMPUS = _when("identityType", ["校外"])
_LIBRARY_GUEST = _when("readerType", ["校外"])
_IT_OTHER = _when("identityType", ["其他"])
_EQUIP_LAB = _when("identityType", ["实验室"])
_PARKING_CAMPUS = _when("ownerType", ["教职工", "学生"])
_PARKING_GUEST = _when("ownerType", ["访客"])


COMMON_PROFILE_FIELDS: list[dict[str, Any]] = [
    _pf("realName", "姓名", required=True, on_register=True, max_length=32),
    _pf("phone", "手机", storage="phone", required=True, on_register=True, max_length=20,
        format="phone", placeholder="11 位手机号"),
    _pf("email", "邮箱", on_register=True, max_length=64, format="email", placeholder="选填"),
    _pf("gender", "性别", on_register=True, field_type="select", options=["男", "女", "保密"]),
]

# 各领域业务档案（不含公共底座；由 attach_profile_fields 合并）
PROFILE_FIELDS_BY_DOMAIN: dict[str, list[dict[str, Any]]] = {
    "DOM-LIBRARY": [
        _pf("readerType", "读者类型", required=True, on_register=True, field_type="select",
            options=["本科生", "研究生", "教职工", "校外"]),
        # 校外读者通常无校内借书证，不可与院系一样对全员必填
        _pf("cardNo", "借书证号", required=True, on_register=True, max_length=32,
            required_when=_LIBRARY_CAMPUS, visible_when=_LIBRARY_CAMPUS,
            placeholder="校内读者填写借书证号"),
        _pf("dept", "院系/单位", required=True, on_register=True, max_length=64,
            required_when=_LIBRARY_CAMPUS, visible_when=_LIBRARY_CAMPUS,
            placeholder="所在院系或单位"),
        _pf("workUnit", "工作单位", on_register=True, max_length=64,
            required_when=_LIBRARY_GUEST, visible_when=_LIBRARY_GUEST,
            placeholder="校外读者填写工作或学习单位"),
        _pf("major", "专业", on_register=True, max_length=64,
            visible_when=_LIBRARY_STUDENT),
        _pf("enrollYear", "入学年份", max_length=16, placeholder="如 2023",
            visible_when=_LIBRARY_STUDENT),
    ],
    "DOM-EQUIP": [
        _pf("identityType", "身份", required=True, on_register=True, field_type="select",
            options=["学生", "教职工", "实验室", "校外"]),
        _pf("studentNo", "学号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["学生"]),
            visible_when=_when("identityType", ["学生"]),
            placeholder="请填写学号"),
        _pf("employeeNo", "工号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["教职工"]),
            visible_when=_when("identityType", ["教职工"]),
            placeholder="请填写工号"),
        _pf("dept", "院系/单位", required=True, on_register=True, max_length=64,
            required_when=_when("identityType", ["学生", "教职工", "实验室"]),
            visible_when=_when("identityType", ["学生", "教职工", "实验室"]),
            placeholder="所在院系、单位或实验室归属"),
        _pf("labOrOffice", "实验室名称", on_register=True, max_length=64,
            required_when=_EQUIP_LAB, visible_when=_EQUIP_LAB,
            placeholder="请填写实验室全称"),
        _pf("orgName", "单位名称", on_register=True, max_length=64,
            required_when=_OFF_CAMPUS, visible_when=_OFF_CAMPUS,
            placeholder="校外请填写单位"),
        _pf("officeLoc", "办公室", on_register=True, max_length=64,
            visible_when=_when("identityType", ["教职工"]),
            placeholder="选填"),
        _pf("contactAlt", "备用联系人", max_length=32),
    ],
    "DOM-ASSET": [
        _pf("identityType", "身份", required=True, on_register=True, field_type="select",
            options=["教职工", "学生", "校外"]),
        _pf("employeeNo", "工号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["教职工"]),
            visible_when=_when("identityType", ["教职工"]),
            placeholder="请填写工号"),
        _pf("studentNo", "学号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["学生"]),
            visible_when=_when("identityType", ["学生"]),
            placeholder="请填写学号"),
        _pf("dept", "部门", required=True, on_register=True, max_length=64,
            required_when=_when("identityType", ["教职工", "学生"]),
            visible_when=_when("identityType", ["教职工", "学生"]),
            placeholder="所在部门或院系"),
        _pf("orgName", "单位名称", on_register=True, max_length=64,
            required_when=_OFF_CAMPUS, visible_when=_OFF_CAMPUS,
            placeholder="校外请填写单位"),
        _pf("jobTitle", "职务", on_register=True, max_length=32,
            visible_when=_when("identityType", ["教职工"])),
        _pf("costCenter", "成本中心/科室", max_length=64,
            visible_when=_when("identityType", ["教职工"])),
        _pf("officeLoc", "办公地点", on_register=True, max_length=64,
            visible_when=_when("identityType", ["教职工"])),
    ],
    "DOM-CRM": [
        _pf("identityType", "身份", required=True, on_register=True, field_type="select",
            options=["教职工", "学生", "校外"]),
        _pf("employeeNo", "工号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["教职工"]),
            visible_when=_when("identityType", ["教职工"])),
        _pf("studentNo", "学号", on_register=True, max_length=32,
            required_when=_when("identityType", ["学生"]),
            visible_when=_when("identityType", ["学生"])),
        _pf("dept", "部门/团队", required=True, on_register=True, max_length=64,
            required_when=_when("identityType", ["教职工", "学生"]),
            visible_when=_when("identityType", ["教职工", "学生"])),
        _pf("orgName", "单位/组织", on_register=True, max_length=64,
            required_when=_OFF_CAMPUS, visible_when=_OFF_CAMPUS,
            placeholder="校外请填写单位或组织"),
        _pf("jobTitle", "岗位", on_register=True, max_length=32, placeholder="如 客户经理",
            visible_when=_when("identityType", ["教职工"])),
        _pf("region", "负责区域", on_register=True, max_length=64,
            visible_when=_when("identityType", ["教职工"])),
        _pf("quotaHint", "业绩目标备注", max_length=64,
            visible_when=_when("identityType", ["教职工"])),
    ],

    "DOM-ATTEND": [
        _pf("identityType", "身份", required=True, on_register=True, field_type="select",
            options=["教职工", "学生"]),
        _pf("employeeNo", "工号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["教职工"]),
            visible_when=_when("identityType", ["教职工"])),
        _pf("studentNo", "学号", on_register=True, max_length=32,
            required_when=_when("identityType", ["学生"]),
            visible_when=_when("identityType", ["学生"])),
        _pf("dept", "部门/院系", required=True, on_register=True, max_length=64),
    ],
    "DOM-RECRUIT": [
        _pf("identityType", "身份", required=True, on_register=True, field_type="select",
            options=["应届生", "往届", "在职"]),
        _pf("studentNo", "学号", on_register=True, max_length=32,
            visible_when=_when("identityType", ["应届生"])),
        _pf("dept", "专业/方向", required=True, on_register=True, max_length=64),
        _pf("jobTitle", "求职意向", on_register=True, max_length=32),
    ],
    "DOM-GRADE": [
        _pf("studentNo", "学号", required=True, on_register=True, max_length=32),
        _pf("dept", "院系", required=True, on_register=True, max_length=64),
        _pf("gradeYear", "年级", on_register=True, max_length=16),
    ],
    "DOM-INTERN": [
        _pf("studentNo", "学号", required=True, on_register=True, max_length=32),
        _pf("dept", "院系", required=True, on_register=True, max_length=64),
        _pf("internOrg", "实习单位", on_register=True, max_length=64),
    ],
    "DOM-PARCEL": [
        _pf("campusNo", "学号/工号", required=True, on_register=True, max_length=32),
        _pf("dept", "院系/部门", required=True, on_register=True, max_length=64),
        _pf("usualPlace", "常用取件点", on_register=True, max_length=64),
        _pf("contactWechat", "联系微信", on_register=True, max_length=32),
    ],

    "DOM-EVENT": [
        _pf("identityType", "身份", required=True, on_register=True, field_type="select",
            options=["教职工", "学生", "校外"]),
        _pf("employeeNo", "工号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["教职工"]),
            visible_when=_when("identityType", ["教职工"])),
        _pf("studentNo", "学号", on_register=True, max_length=32,
            required_when=_when("identityType", ["学生"]),
            visible_when=_when("identityType", ["学生"])),
        _pf("dept", "部门/网格", required=True, on_register=True, max_length=64,
            required_when=_when("identityType", ["教职工", "学生"]),
            visible_when=_when("identityType", ["教职工", "学生"])),
        _pf("orgName", "单位/组织", on_register=True, max_length=64,
            required_when=_OFF_CAMPUS, visible_when=_OFF_CAMPUS,
            placeholder="校外请填写单位或组织"),
        _pf("jobTitle", "岗位", on_register=True, max_length=32, placeholder="如 网格员",
            visible_when=_when("identityType", ["教职工"])),
        _pf("region", "负责网格/区域", on_register=True, max_length=64,
            visible_when=_when("identityType", ["教职工"])),
    ],
    "DOM-DORM": [
        _pf("studentNo", "学号", required=True, on_register=True, max_length=32),
        _pf("college", "学院", required=True, on_register=True, max_length=64),
        _pf("className", "班级", required=True, on_register=True, max_length=64),
        _pf("grade", "年级", on_register=True, max_length=16, placeholder="如 2023 级"),
        _pf("dormBuilding", "楼栋", required=True, on_register=True, max_length=32, placeholder="如 一号楼"),
        _pf("dormRoom", "房间", required=True, on_register=True, max_length=16, placeholder="如 101"),
        _pf("bedNo", "床位", max_length=8),
    ],
    "DOM-PROPERTY": [
        _pf("houseBuilding", "楼栋", required=True, on_register=True, max_length=32),
        _pf("houseUnit", "单元", on_register=True, max_length=16),
        _pf("houseNo", "房号", required=True, on_register=True, max_length=16),
        _pf("ownerType", "住户类型", required=True, on_register=True, field_type="select",
            options=["业主", "租户", "家属"]),
        _pf("parkingNo", "车位号", max_length=32),
        _pf("emergencyContact", "紧急联系人", max_length=32),
        _pf("emergencyPhone", "紧急联系电话", max_length=20),
    ],
    "DOM-IT": [
        _pf("identityType", "身份", required=True, on_register=True, field_type="select",
            options=["学生", "教职工", "其他"]),
        _pf("studentNo", "学号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["学生"]),
            visible_when=_when("identityType", ["学生"]),
            placeholder="请填写学号"),
        _pf("employeeNo", "工号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["教职工"]),
            visible_when=_when("identityType", ["教职工"]),
            placeholder="请填写工号"),
        _pf("dept", "院系/单位", required=True, on_register=True, max_length=64,
            required_when=_IT_CAMPUS, visible_when=_IT_CAMPUS,
            placeholder="所在院系或单位"),
        _pf("orgName", "单位名称", on_register=True, max_length=64,
            required_when=_IT_OTHER, visible_when=_IT_OTHER,
            placeholder="其他人员填写所在单位"),
        _pf("officeOrDorm", "办公/宿舍地址", on_register=True, max_length=64,
            visible_when=_IT_CAMPUS, placeholder="选填"),
        _pf("title", "职务/年级", max_length=32,
            visible_when=_IT_CAMPUS, placeholder="选填"),
    ],
    "DOM-ACTIVITY": [
        _pf("identityType", "身份", required=True, on_register=True, field_type="select",
            options=["学生", "教职工", "校外"]),
        _pf("studentNoOrEmp", "学号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["学生"]), visible_when=_when("identityType", ["学生"]),
            placeholder="请填写学号"),
        _pf("employeeNo", "工号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["教职工"]), visible_when=_when("identityType", ["教职工"]),
            placeholder="请填写工号"),
        _pf("dept", "院系/单位", required=True, on_register=True, max_length=64,
            required_when=_CAMPUS_ID, visible_when=_CAMPUS_ID,
            placeholder="所在院系或单位"),
        _pf("orgOrClub", "单位/组织", on_register=True, max_length=64,
            required_when=_OFF_CAMPUS, visible_when=_OFF_CAMPUS,
            placeholder="校外请填写所在单位或组织"),
        _pf("clubName", "社团/组织", on_register=True, max_length=64,
            visible_when=_CAMPUS_ID,
            placeholder="选填，如所属社团"),
        _pf("emergencyPhone", "紧急联系电话", max_length=20),
    ],
    "DOM-LOST": [
        _pf("campusNo", "学号/工号", on_register=True, max_length=32),
        _pf("dept", "院系/单位", on_register=True, max_length=64),
        _pf("contactWechat", "微信/备用联系", on_register=True, max_length=64),
        _pf("usualPlace", "常出现区域", max_length=64),
    ],
    "DOM-COURSE": [
        _pf("studentNo", "学号", required=True, on_register=True, max_length=32),
        _pf("college", "学院", required=True, on_register=True, max_length=64),
        _pf("major", "专业", required=True, on_register=True, max_length=64),
        _pf("className", "班级", required=True, on_register=True, max_length=64),
        _pf("grade", "年级", on_register=True, max_length=16),
        _pf("enrollYear", "入学年份", max_length=16),
    ],
    "DOM-SHOP": [
        # 校园二手 / 社会电商共用：不绑死「校内/校外」
        _pf("deliveryType", "收货方式", required=True, on_register=True, field_type="select",
            options=["配送到家", "到店自提"]),
        _pf("receiverName", "收货人", required=True, on_register=True, max_length=32),
        _pf("receiveAddress", "收货地址", required=True, on_register=True, max_length=128,
            required_when=_when("deliveryType", ["配送到家"]),
            visible_when=_when("deliveryType", ["配送到家"]),
            placeholder="小区、写字楼、宿舍楼栋等均可"),
        _pf("pickupPoint", "自提点备注", on_register=True, max_length=64,
            visible_when=_when("deliveryType", ["到店自提"]),
            placeholder="选填，如门店名或取货码偏好"),
        _pf("defaultRemark", "下单备注偏好", max_length=128),
    ],
    "DOM-FOOD": [
        # 食堂窗口 / 社会餐饮外卖共用
        _pf("receiverName", "联系人", required=True, on_register=True, max_length=32,
            placeholder="取餐人或收餐人"),
        _pf("pickupType", "用餐方式", required=True, on_register=True, field_type="select",
            options=["堂食", "外卖配送", "到店自取"]),
        _pf("preferredStore", "常去门店/窗口", on_register=True, max_length=64,
            visible_when=_when("pickupType", ["堂食", "到店自取"]),
            placeholder="选填"),
        _pf("deliveryAddress", "配送地址", on_register=True, max_length=128,
            required_when=_when("pickupType", ["外卖配送"]),
            visible_when=_when("pickupType", ["外卖配送"]),
            placeholder="小区、写字楼、宿舍等"),
        _pf("memberNo", "会员号", on_register=True, max_length=32, placeholder="选填"),
        _pf("allergyNote", "忌口说明", max_length=128),
    ],
    "DOM-HOSPITAL": [
        _pf("patientNo", "就诊卡号", required=True, on_register=True, max_length=32),
        _pf("idTypeHint", "证件类型", on_register=True, field_type="select",
            options=["身份证", "护照", "其他"]),
        _pf("deptPrefer", "常挂科室", max_length=64),
        _pf("allergyNote", "过敏史简述", max_length=128),
        _pf("emergencyContact", "紧急联系人", max_length=32),
        _pf("emergencyPhone", "紧急联系电话", max_length=20),
    ],
    "DOM-PARKING": [
        _pf("plateNo", "车牌号", required=True, on_register=True, max_length=16),
        _pf("vehicleType", "车辆类型", required=True, on_register=True, field_type="select",
            options=["小型车", "新能源", "摩托车"]),
        _pf("ownerType", "车主身份", required=True, on_register=True, field_type="select",
            options=["教职工", "学生", "访客"]),
        # 访客无学号/工号；校内再按身份区分字段更清晰
        _pf("employeeNo", "工号", on_register=True, max_length=32,
            required_when=_when("ownerType", ["教职工"]),
            visible_when=_when("ownerType", ["教职工"]),
            placeholder="请填写工号"),
        _pf("studentNo", "学号", on_register=True, max_length=32,
            required_when=_when("ownerType", ["学生"]),
            visible_when=_when("ownerType", ["学生"]),
            placeholder="请填写学号"),
        _pf("dept", "单位", on_register=True, max_length=64,
            required_when=_PARKING_CAMPUS, visible_when=_PARKING_CAMPUS,
            placeholder="所在院系或单位"),
        _pf("visitUnit", "来访单位", on_register=True, max_length=64,
            required_when=_PARKING_GUEST, visible_when=_PARKING_GUEST,
            placeholder="访客请填写来访单位或事由相关单位"),
    ],
    "DOM-MEETING": [
        _pf("identityType", "身份", required=True, on_register=True, field_type="select",
            options=["学生", "教职工", "校外"]),
        _pf("studentNo", "学号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["学生"]),
            visible_when=_when("identityType", ["学生"])),
        _pf("employeeNo", "工号", required=True, on_register=True, max_length=32,
            required_when=_when("identityType", ["教职工"]),
            visible_when=_when("identityType", ["教职工"])),
        _pf("dept", "院系/部门", required=True, on_register=True, max_length=64,
            required_when=_CAMPUS_ID, visible_when=_CAMPUS_ID),
        _pf("orgName", "单位名称", on_register=True, max_length=64,
            required_when=_OFF_CAMPUS, visible_when=_OFF_CAMPUS,
            placeholder="校外请填写单位"),
        _pf("jobTitle", "职务", on_register=True, max_length=32,
            visible_when=_when("identityType", ["教职工"])),
        _pf("officePhone", "办公电话", max_length=20,
            visible_when=_when("identityType", ["教职工"])),
    ],
    "DOM-SALON": [
        _pf("memberNo", "会员号", on_register=True, max_length=32),
        _pf("skinOrPrefer", "偏好备注", max_length=128),
        _pf("birthday", "生日", max_length=16, placeholder="如 01-15"),
        _pf("emergencyPhone", "紧急联系电话", max_length=20),
    ],
    "DOM-HOTEL": [
        _pf("guestName", "入住人", required=True, on_register=True, max_length=32),
        _pf("idTypeHint", "证件类型", on_register=True, field_type="select",
            options=["身份证", "护照", "其他"]),
        _pf("companyOrSchool", "单位/学校", on_register=True, max_length=64),
        _pf("arrivePrefer", "预计到达时段", field_type="select",
            options=["上午", "下午", "晚上"]),
        _pf("emergencyPhone", "紧急联系电话", max_length=20),
    ],
    "DOM-GENERIC": [
        _pf("orgName", "所属单位", on_register=True, max_length=64),
        _pf("jobTitle", "职务", max_length=32),
        _pf("employeeNo", "工号", on_register=True, max_length=32),
    ],
    "DOM-MEDIA": [
        _pf("memberNo", "会员号", on_register=True, max_length=32),
        _pf("orgName", "学校/单位", on_register=True, max_length=64),
        _pf("preferredGenre", "偏好类型", on_register=True, field_type="select",
            options=["电影", "电视剧", "综艺", "动漫", "纪录片", "不限"]),
    ],
    "DOM-MUSIC": [
        _pf("memberNo", "会员号", on_register=True, max_length=32),
        _pf("orgName", "学校/单位", on_register=True, max_length=64),
        _pf("preferredGenre", "偏好曲风", on_register=True, field_type="select",
            options=["流行", "摇滚", "民谣", "电子", "古典", "不限"]),
    ],
    "DOM-FORUM": [
        _pf("memberNo", "用户号", on_register=True, max_length=32),
        _pf("orgName", "学院/单位", on_register=True, max_length=64),
        _pf("preferredGenre", "偏好板块", on_register=True, field_type="select",
            options=["学习交流", "校园生活", "二手信息", "求助问答", "不限"]),
    ],
    "DOM-BLOG": [
        _pf("memberNo", "读者号", on_register=True, max_length=32),
        _pf("orgName", "学校/单位", on_register=True, max_length=64),
        _pf("preferredGenre", "偏好栏目", on_register=True, field_type="select",
            options=["技术", "随笔", "资讯", "教程", "不限"]),
    ],
}


def profile_fields_for(domain: str) -> list[dict[str, Any]]:
    """公共底座全角色可用；领域业务档案默认仅终端用户（患者/车主等），管理岗不填。"""
    specific = copy.deepcopy(
        PROFILE_FIELDS_BY_DOMAIN.get(domain) or PROFILE_FIELDS_BY_DOMAIN["DOM-GENERIC"]
    )
    for f in specific:
        if isinstance(f, dict):
            f.setdefault("forRoles", ["user"])
    return copy.deepcopy(COMMON_PROFILE_FIELDS) + specific


def attach_profile_fields(schema: dict[str, Any], domain: str) -> dict[str, Any]:
    out = copy.deepcopy(schema)
    out["profileFields"] = profile_fields_for(domain)
    return out
