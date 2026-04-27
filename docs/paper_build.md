# LaTeX 论文编译说明

论文主文件：`docs/paper.tex`

## 1) 本机安装（任选）

- macOS (MacTeX):  
  `brew install --cask mactex-no-gui`
- 或使用 TinyTeX:
  `brew install --cask tinytex`

## 2) 编译命令

在项目根目录执行：

```bash
xelatex -interaction=nonstopmode -halt-on-error docs/paper.tex
xelatex -interaction=nonstopmode -halt-on-error docs/paper.tex
```

输出文件：`docs/paper.pdf`

## 3) 说明

- 当前文稿已包含：摘要、问题定义、方法、五类实验、结果表格、讨论与结论。
- 若需投稿版（双栏模板、参考文献格式、匿名化），可在此基础上切换到目标会议模板继续排版。

