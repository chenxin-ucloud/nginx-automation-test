#!/bin/bash
# 测试执行入口脚本
# 用于运行各种组合的测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
REPORT_DIR="reports"
LOG_DIR="logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/report_$TIMESTAMP.html"

# 帮助信息
usage() {
    echo "Nginx 自动化测试执行脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -p, --priority P0|P1|P2|P3  按优先级运行测试 (默认: P0)"
    echo "  -m, --module MODULE         指定测试模块运行"
    echo "  -a, --all                   运行所有测试"
    echo "  -f, --file FILE             运行指定测试文件"
    echo "  -n, --parallel N            并行运行测试 (N个进程)"
    echo "  -r, --reruns N              失败重试次数"
    echo "  -h, --help                  显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -p P0                    运行P0优先级测试"
    echo "  $0 -p 'P0 or P1'            运行P0和P1优先级测试"
    echo "  $0 -m proxy_set_header      运行proxy_set_header模块测试"
    echo "  $0 -f tests/test_server.py  运行指定测试文件"
    echo "  $0 -a                       运行所有测试"
    echo "  $0 -a -n 4                  并行运行所有测试(4进程)"
    echo ""
}

# 解析参数
PRIORITY=""
MODULE=""
FILE=""
ALL=false
PARALLEL=""
RERUNS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--priority)
            PRIORITY="$2"
            shift 2
            ;;
        -m|--module)
            MODULE="$2"
            shift 2
            ;;
        -f|--file)
            FILE="$2"
            shift 2
            ;;
        -a|--all)
            ALL=true
            shift
            ;;
        -n|--parallel)
            PARALLEL="$2"
            shift 2
            ;;
        -r|--reruns)
            RERUNS="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}错误: 未知选项 $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# 创建目录
mkdir -p $REPORT_DIR
mkdir -p $LOG_DIR

# 构建pytest命令
PYTEST_CMD="pytest"

# 添加测试路径
if [ -n "$FILE" ]; then
    PYTEST_CMD="$PYTEST_CMD $FILE"
elif [ "$ALL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD tests/"
elif [ -n "$MODULE" ]; then
    PYTEST_CMD="$PYTEST_CMD tests/test_$MODULE.py"
else
    # 默认运行P0测试
    if [ -z "$PRIORITY" ]; then
        PRIORITY="P0"
    fi
    PYTEST_CMD="$PYTEST_CMD tests/"
fi

# 添加优先级标记
if [ -n "$PRIORITY" ]; then
    PYTEST_CMD="$PYTEST_CMD -m '$PRIORITY'"
fi

# 添加基本选项
PYTEST_CMD="$PYTEST_CMD -v --tb=short --strict-markers"

# 添加HTML报告
PYTEST_CMD="$PYTEST_CMD --html=$REPORT_FILE --self-contained-html"

# 添加并行执行
if [ -n "$PARALLEL" ]; then
    PYTEST_CMD="$PYTEST_CMD -n $PARALLEL"
fi

# 添加失败重试
if [ -n "$RERUNS" ]; then
    PYTEST_CMD="$PYTEST_CMD --reruns $RERUNS --reruns-delay 1"
fi

# 显示执行信息
echo -e "${BLUE}=== Nginx 自动化测试 ===${NC}"
echo ""
if [ -n "$PRIORITY" ]; then
    echo -e "优先级: ${YELLOW}$PRIORITY${NC}"
fi
if [ -n "$MODULE" ]; then
    echo -e "模块: ${YELLOW}$MODULE${NC}"
fi
if [ -n "$FILE" ]; then
    echo -e "测试文件: ${YELLOW}$FILE${NC}"
fi
if [ "$ALL" = true ]; then
    echo -e "运行: ${YELLOW}所有测试${NC}"
fi
if [ -n "$PARALLEL" ]; then
    echo -e "并行进程: ${YELLOW}$PARALLEL${NC}"
fi
echo -e "报告文件: ${YELLOW}$REPORT_FILE${NC}"
echo ""
echo -e "执行命令: ${GREEN}$PYTEST_CMD${NC}"
echo ""

# 执行测试
eval $PYTEST_CMD

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=== 测试通过 ===${NC}"
else
    echo -e "${RED}=== 测试失败 (退出码: $EXIT_CODE) ===${NC}"
fi

echo ""
echo "报告文件: $REPORT_FILE"

exit $EXIT_CODE
