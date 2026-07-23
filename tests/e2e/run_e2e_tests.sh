#!/bin/bash
# E2E Test Runner Script
# E2E测试运行脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认配置
ENV_FILE=".env"
COMPOSE_FILE="docker-compose.test.yml"
PARALLEL=false
VERBOSE=false
COVERAGE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --parallel)
            PARALLEL=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --help)
            echo "E2E Test Runner Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --parallel    Run tests in parallel"
            echo "  --verbose     Enable verbose output"
            echo "  --coverage    Generate coverage report"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Starting E2E Test Runner${NC}"
echo "=============================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# 启动测试环境
echo -e "${YELLOW}Starting test environment...${NC}"
docker-compose -f $COMPOSE_FILE up -d

# 等待服务就绪
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# 检查服务健康状态
echo -e "${YELLOW}Checking service health...${NC}"
docker-compose -f $COMPOSE_FILE ps

# 加载环境变量
if [ -f "$ENV_FILE" ]; then
    export $(cat $ENV_FILE | grep -v '^#' | xargs)
    echo -e "${GREEN}Environment variables loaded${NC}"
else
    echo -e "${YELLOW}Warning: .env file not found, using defaults${NC}"
fi

# 构建pytest命令
PYTEST_CMD="pytest tests/e2e/ -v -m e2e"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -s --log-cli-level=DEBUG"
fi

if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --e2e-parallel -n 4"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=core --cov=api --cov-report=html --cov-report=term"
fi

# 运行测试
echo -e "${GREEN}Running E2E tests...${NC}"
echo "Command: $PYTEST_CMD"
echo "=============================="

if eval $PYTEST_CMD; then
    TEST_RESULT=0
    echo -e "${GREEN}✓ All E2E tests passed${NC}"
else
    TEST_RESULT=1
    echo -e "${RED}✗ Some E2E tests failed${NC}"
fi

# 清理测试环境
echo -e "${YELLOW}Cleaning up test environment...${NC}"
docker-compose -f $COMPOSE_FILE down -v

# 生成测试报告
if [ "$COVERAGE" = true ]; then
    echo -e "${GREEN}Coverage report generated in htmlcov/${NC}"
fi

# 退出
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}==============================${NC}"
    echo -e "${GREEN}E2E Test Runner completed successfully${NC}"
    exit 0
else
    echo -e "${RED}==============================${NC}"
    echo -e "${RED}E2E Test Runner completed with failures${NC}"
    exit 1
fi