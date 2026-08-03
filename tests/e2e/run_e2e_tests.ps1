# E2E Test Runner Script for Windows
# E2E测试运行脚本（Windows版本）

param(
    [switch]$Parallel,
    [switch]$Verbose,
    [switch]$Coverage,
    [switch]$Help
)

# 显示帮助信息
if ($Help) {
    Write-Host "E2E Test Runner Script (Windows)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\run_e2e_tests.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Parallel    Run tests in parallel"
    Write-Host "  -Verbose     Enable verbose output"
    Write-Host "  -Coverage    Generate coverage report"
    Write-Host "  -Help        Show this help message"
    exit 0
}

Write-Host "Starting E2E Test Runner" -ForegroundColor Green
Write-Host "=============================="

# 默认配置
$EnvFile = ".env"
$ComposeFile = "docker-compose.test.yml"

# 检查Docker是否运行
try {
    docker info | Out-Null
} catch {
    Write-Host "Error: Docker is not running" -ForegroundColor Red
    exit 1
}

# 启动测试环境
Write-Host "Starting test environment..." -ForegroundColor Yellow
docker-compose -f $ComposeFile up -d

# 等待服务就绪
Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 检查服务健康状态
Write-Host "Checking service health..." -ForegroundColor Yellow
docker-compose -f $ComposeFile ps

# 加载环境变量
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | Where-Object { $_ -notmatch '^#' } | ForEach-Object {
        $parts = $_.split('=')
        if ($parts.Length -eq 2) {
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim())
        }
    }
    Write-Host "Environment variables loaded" -ForegroundColor Green
} else {
    Write-Host "Warning: .env file not found, using defaults" -ForegroundColor Yellow
}

# 构建pytest命令
$Env:AIOPS_RUN_API_TESTS = "1"
$PytestCmd = "python -m pytest tests/e2e/ -v -m e2e -o 'addopts=--strict-markers --disable-warnings --tb=short -p no:unraisableexception'"

if ($Verbose) {
    $PytestCmd = "$PytestCmd -s --log-cli-level=DEBUG"
}

if ($Parallel) {
    $PytestCmd = "$PytestCmd --e2e-parallel -n 4"
}

if ($Coverage) {
    $PytestCmd = "$PytestCmd --cov=core --cov=api --cov-report=html --cov-report=term"
}

# 运行测试
Write-Host "Running E2E tests..." -ForegroundColor Green
Write-Host "Command: $PytestCmd"
Write-Host "=============================="

$TestResult = & python -m pytest tests/e2e/ -v -m e2e -o 'addopts=--strict-markers --disable-warnings --tb=short -p no:unraisableexception' 

if ($LASTEXITCODE -eq 0) {
    Write-Host "All E2E tests passed" -ForegroundColor Green
} else {
    Write-Host "Some E2E tests failed" -ForegroundColor Red
}

# 清理测试环境
Write-Host "Cleaning up test environment..." -ForegroundColor Yellow
docker-compose -f $ComposeFile down -v

# 生成测试报告
if ($Coverage) {
    Write-Host "Coverage report generated in htmlcov/" -ForegroundColor Green
}

# 退出
if ($LASTEXITCODE -eq 0) {
    Write-Host "==============================" -ForegroundColor Green
    Write-Host "E2E Test Runner completed successfully" -ForegroundColor Green
    exit 0
} else {
    Write-Host "==============================" -ForegroundColor Red
    Write-Host "E2E Test Runner completed with failures" -ForegroundColor Red
    exit 1
}