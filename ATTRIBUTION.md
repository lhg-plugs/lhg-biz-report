# 灵感来源与致谢（Attribution）

本插件的**方法论灵感**来自以下优秀的开源项目，**所有实现代码、检测规则与文案均为原创**，未复制任何第三方的原文案与代码。

| 项目 | 作者 / 组织 | 许可 | 链接 | 借鉴了什么思路 |
|---|---|---|---|---|
| felaris/claude-skills 中的商业分析 skill | felaris | 许可未声明（仅借鉴高层思路） | https://github.com/felaris/claude-skills | "原始数据→洞察→报告"分阶段工作流的高层思路：先统一口径再分析、分析与呈现分离。本插件的四阶段流水线（接入→口径→洞察→交付）受其启发。**因其许可未声明，仅借鉴高层思路，未复制任何文案与代码** |
| lhg-excel（lhg-plugs 组织自有） | 刘洪光 | MIT | https://github.com/lhg-plugs/lhg-excel | **复用关系**：本插件 `lhg-br-intake` 的数据清洗方法论复用其 `lhg-ex-clean`（清洗五步法）与 `lhg-ex-opslog`（操作日志规范）；SKILL.md 中已明确标注复用，细节以 lhg-excel 为准 |
| lhg-ppt（lhg-plugs 组织自有） | 刘洪光 | MIT | https://github.com/lhg-plugs/lhg-ppt | **复用关系**：本插件 `lhg-br-deliver` 的大纲方法论复用其 `lhg-ppt-outline`（金字塔大纲），PPT 页面构建走其 `lhg-ppt-build`；SKILL.md 中已明确标注复用 |

## 声明

1. **借鉴思路，实现与文案均为原创**：以上项目的具体文案、规则原文、代码实现均未被复制。本插件的 skill 方法论文案、审计规则、命令流程、hook 脚本均为独立撰写。
2. **许可合规**：lhg-excel / lhg-ppt 为本组织自有 MIT 许可项目，复用其方法论并已在 SKILL.md 与本文件中明确标注；felaris/claude-skills 许可未声明，仅借鉴高层思路，未复制任何内容。
3. **商标与归属**：各项目名称与作者署名归其各自所有者所有。
4. **未核实项**：felaris/claude-skills 仓库的 star 数与具体 skill 实现细节未核实，本插件不以其热度背书，也不依赖其具体实现。

## 本插件自身的许可

本插件原创部分采用 MIT 许可（见 `LICENSE` 文件），版权所有：刘洪光（https://github.com/lhg-skills）。
