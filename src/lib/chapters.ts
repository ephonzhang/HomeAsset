export type ChapterMeta = {
  to: string;
  no: string;
  label: string;
  sub: string;
  intro: string;
};

export const chapters: ChapterMeta[] = [
  {
    to: "/",
    no: "01",
    label: "扉页",
    sub: "资产总览",
    intro: "你的资产总数字、收益概要与配置结构一览。",
  },
  {
    to: "/holdings",
    no: "02",
    label: "持仓透视",
    sub: "明细与配置",
    intro: "全量标的、市值、股息与税务明细，可逐行下钻。",
  },
  {
    to: "/dividend",
    no: "03",
    label: "股息收益",
    sub: "贡献与税负",
    intro: "股息贡献、税务与全年派息节奏的多维度拆解。",
  },
  {
    to: "/history",
    no: "04",
    label: "时间线",
    sub: "历史与快照",
    intro: "历史快照对比与资产 / 股息的趋势线。",
  },
  {
    to: "/settings",
    no: "05",
    label: "档案",
    sub: "设置与口径",
    intro: "汇率口径、数据来源、导出与系统信息。",
  },
];

export function findChapter(path: string): ChapterMeta {
  return chapters.find((c) => c.to === path) ?? chapters[0];
}