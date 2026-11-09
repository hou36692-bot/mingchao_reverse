# 鸣潮卡提希娅角色渲染还原

*Wuthering Waves · Katixiya character rendering reconstruction in Unreal Engine 5.8*

以《鸣潮》卡提希娅选人界面为参考，从 D3D11 帧捕获出发，在 UE 5.8 中重建角色材质、描边、背景、后处理与 UI。工程保留默认 Renderer / Substrate，用可编辑 Shader 函数、材质实例和运行时输入表达源渲染管线。

> 个人研究项目，与库洛游戏无关。仓库包含游戏模型、贴图等派生内容，权利归原权利人所有；仅供研究与展示。整体视觉 1∶1 未验收。

![结项时保存的 UE 画面](docs/figures/01-final-4k.png)

*原生 3840×2160，结项时保存的 UE 画面。*

## 效果

![阶段成果总览](docs/figures/02-overview.jpg)

*从源帧到结项的六个阶段。总览为缩放排版，跨阶段条件不同，不用于像素误差比较。*

## 项目简述

| 项目 | 内容 |
| --- | --- |
| 参考 | 《鸣潮》卡提希娅选人界面，D3D11 / Frame 3765 / 3840×2160 |
| 引擎 | Unreal Engine 5.8，默认 Renderer / Substrate |
| 实现 | 8 个主体材质槽、6 组描边、HET／前发辅助、22 个背景实例、U5 后处理、U6 UI |
| 方法 | RDC 语义分析 → 可读 HLSL／材质函数 → MPC／RT 运行时驱动 → 同条件验证 |

## 打开工程

1. 安装 UE 5.8、Visual Studio C++ 工具链和 Git LFS；执行 `git lfs install` 后克隆，并运行 `git lfs pull` 获取完整资产。
2. 打开 `mingchao_reverse.uproject`。首次打开需要编译 C++ 模块。
3. 加载 `/Game/Maps/L_Katixiya_Reference`；默认启动地图是 ThirdPerson 模板。

## 已知边界

工程交付完成，整体视觉 1∶1 未验收。反射、Ribbon 实例、姿态与部分采样残差保留；受控响应测试不等于最终视觉验收。

## 许可

原创代码、Shader、文档与截图以 MIT 发布，版权人 hou。游戏名称、角色、模型、贴图等权利归原权利人所有，详见 [NOTICE](NOTICE.md)。
