# 鸣潮卡提希娅渲染重建

一次 AI 辅助渲染逆向实验，以《鸣潮》卡提希娅选人界面为例，走通捕获分析、源资产匹配、UE 导入、材质语义与运行时输入重建、后处理及受控验证。

项目已结项，完成 R2–R7 语义重建工程交付，包含可编辑材质、Shader 函数、运行时 Render Target、背景与参考界面。**整体视觉 1∶1 未验收**，仍保留部分反射、背景实例和局部视觉差异。

## 打开工程

1. 安装 Unreal Engine **5.8**、Visual Studio C++ 编译工具链和 Git LFS。工程包含 C++ 模块及 `UE_MCP_Bridge` 插件源码，首次打开需要编译。
2. 先执行 `git lfs install`，再通过仓库页面的 **Code** 地址克隆工程；进入工程目录执行 `git lfs pull`，确保下载的是完整资产。请使用 Git 克隆，避免仅下载 ZIP 后缺少 LFS 资产。
3. 打开 `mingchao_reverse.uproject`。如果提示缺少模块，允许重新编译；也可先生成 Visual Studio 项目文件，构建 `Development Editor / Win64`。
4. 手动打开 `/Game/Maps/L_Katixiya_Reference`。默认启动地图仍是 ThirdPerson 模板地图，参考内容位于上述关卡；点击 Play 可查看运行效果。

PIE 中点击画面空白处取得焦点，按英文分号 `;` 进入或退出自由相机；`W/A/S/D` 移动，`E/Q` 升降，按住鼠标右键转向，滚轮调速。自由视角用于观察，视觉对照仍以原参考镜头为准。

## 主要目录

- `Content/MingchaoReverse/`：角色、材质、运行时驱动、背景与 UI。
- `Content/Maps/L_Katixiya_Reference.umap`：参考关卡。
- `Shaders/SemanticRebuild/`：按模块语义整理的 Shader 函数。
- `Source/`、`Plugins/`：项目 C++ 模块与插件源码。
- `Tools/SemanticRebuild/`：部分材质构建脚本，打开工程不需要执行；运行前应检查其写入范围。

本仓库提供已保存的 UE 工程，不包含原始捕获包、解包工具或完整研究资料。模型、纹理及相关游戏内容的权利归原权利人所有；仓库访问权限不代表获得这些内容的再分发或商业使用授权。
