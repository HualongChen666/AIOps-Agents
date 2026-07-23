# Devin Desktop 扩展清理计划

## 🎯 清理目标
基于AIOps Agent项目技术栈，清理不必要的扩展，优化Devin IDE性能。

## 📋 扩展清理清单

### ✅ 保留扩展 (必需)

#### 编程语言支持
- python
- sql
- yaml
- json
- markdown-basics
- markdown-language-features
- shellscript
- docker

#### 版本控制
- git
- git-base

#### 核心功能
- search-result
- configuration-editing
- diff
- merge-conflict
- references-view

#### Devin核心
- windsurf
- windsurf-dev-containers
- windsurf-remote-openssh
- windsurf-remote-wsl

### ⚠️ 条件保留扩展 (根据使用情况)

#### 前端相关 (如果项目有前端)
- javascript
- typescript-basics
- typescript-language-features
- html
- css
- css-language-features

#### 调试相关
- debug-auto-launch
- debug-server-ready

#### 其他功能
- media-preview
- simple-browser
- terminal-suggest
- dotenv
- ipynb

#### Windows环境
- powershell
- bat

#### 主题 (保留1-2个)
- theme-windsurf
- theme-defaults

### ❌ 删除扩展 (不需要)

#### GitHub相关 (项目使用GitLab)
- github
- github-authentication

#### 不相关编程语言
- java
- cpp
- csharp
- go
- rust
- ruby
- php
- fsharp
- groovy
- julia
- lua
- perl
- r
- swift
- objective-c
- dart
- clojure
- coffeescript
- vb

#### JavaScript调试 (项目主要Python)
- ms-vscode.js-debug
- ms-vscode.js-debug-companion
- ms-vscode.vscode-js-profile-table

#### Microsoft认证 (使用GitLab)
- microsoft-authentication

#### 构建工具 (项目不需要)
- grunt
- gulp
- jake
- npm
- node_modules

#### 其他工具
- log
- shaderlab
- hlsl
- razor
- handlebars
- pug
- less
- scss
- stylus
- sass
- restructuredtext
- latex
- make
- cmake (如果有)

#### 多余主题
- theme-2026
- theme-abyss
- theme-kimbie-dark
- theme-monokai
- theme-monokai-dimmed
- theme-quietlight
- theme-red
- theme-seti
- theme-solarized-dark
- theme-solarized-light
- theme-symbols
- theme-synthwave
- theme-tokyo-night
- theme-tomorrow-night-blue

## 🔧 清理命令

### 删除不需要的扩展
```powershell
# GitHub相关
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\github" -Recurse -Force
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\github-authentication" -Recurse -Force

# 不相关编程语言
$unwantedLanguages = @("java","cpp","csharp","go","rust","ruby","php","fsharp","groovy","julia","lua","perl","r","swift","objective-c","dart","clojure","coffeescript","vb")
foreach ($lang in $unwantedLanguages) {
    Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\$lang" -Recurse -Force -ErrorAction SilentlyContinue
}

# JavaScript调试
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\ms-vscode.js-debug" -Recurse -Force
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\ms-vscode.js-debug-companion" -Recurse -Force
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\ms-vscode.vscode-js-profile-table" -Recurse -Force

# Microsoft认证
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\microsoft-authentication" -Recurse -Force

# 构建工具
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\grunt" -Recurse -Force
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\gulp" -Recurse -Force
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\jake" -Recurse -Force
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\npm" -Recurse -Force
Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\node_modules" -Recurse -Force

# 多余主题
$unwantedThemes = @("theme-2026","theme-abyss","theme-kimbie-dark","theme-monokai","theme-monokai-dimmed","theme-quietlight","theme-red","theme-seti","theme-solarized-dark","theme-solarized-light","theme-symbols","theme-synthwave","theme-tokyo-night","theme-tomorrow-night-blue")
foreach ($theme in $unwantedThemes) {
    Remove-Item "C:\Users\Hualong_Chen\AppData\Local\Programs\Devin\resources\app\extensions\$theme" -Recurse -Force -ErrorAction SilentlyContinue
}
```

## 📊 预期效果

清理后预期：
- 减少扩展数量约60%
- 减少内存占用约30%
- 提升IDE启动速度约20%
- 保持所有必需功能
- 优化开发体验

## ⚠️ 注意事项

1. 清理前请备份Devin配置
2. 清理后需要重启Devin IDE
3. 如有需要可以重新安装扩展
4. 建议在非工作时间执行清理

## 🔄 回滚方案

如果清理后出现问题，可以：
1. 重新安装Devin Desktop
2. 手动安装需要的扩展
3. 从备份恢复配置