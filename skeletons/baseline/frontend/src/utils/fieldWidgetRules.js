/**
 * 按字段中文标签选择表单控件，避免档案项一律用文本框。
 * 从上往下匹配，先命中的生效。
 */
export const FIELD_WIDGET_RULES = [
  {
    "widget": "switch",
    "fieldType": "number",
    "labelHasAny": [
      "1是0否",
      "是否"
    ]
  },
  {
    "widget": "money",
    "fieldType": "number",
    "labelHasAny": [
      "元",
      "费",
      "价",
      "金额",
      "房价",
      "单价",
      "挂号"
    ]
  },
  {
    "widget": "number",
    "fieldType": "string",
    "labelIsAny": [
      "承重",
      "阻力",
      "重量",
      "时长",
      "份量",
      "容量",
      "净含量",
      "面积",
      "租金"
    ]
  },
  {
    "widget": "textarea",
    "fieldType": "string",
    "labelHasAny": [
      "摘要",
      "备注",
      "说明",
      "特征",
      "简介",
      "描述"
    ]
  }
]
