#!/usr/bin/env bash
# 文献综述 AI Agent Pipeline — 安装脚本 (macOS / Linux)
set -e

SKILL_DIR="${HOME}/.workbuddy/skills"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills"

echo "================================================"
echo " 文献综述 AI Agent Pipeline — 安装"
echo "================================================"
echo "源目录  : ${SRC_DIR}"
echo "目标目录: ${SKILL_DIR}"
echo

if [ ! -d "${SRC_DIR}" ]; then
    echo "[ERROR] 找不到 skills 目录: ${SRC_DIR}"
    exit 1
fi

mkdir -p "${SKILL_DIR}"

count=0
for skill in "${SRC_DIR}"/lr-*; do
    [ -d "${skill}" ] || continue
    name="$(basename "${skill}")"

    if [ -d "${SKILL_DIR}/${name}" ]; then
        echo "  [更新] ${name}"
    else
        echo "  [新增] ${name}"
    fi

    mkdir -p "${SKILL_DIR}/${name}"
    cp -r "${skill}"/. "${SKILL_DIR}/${name}/"
    count=$((count + 1))
done

echo
echo "已安装 ${count} 个 Skill 到 ${SKILL_DIR}"
echo

# 安装 Python 依赖
if command -v pip3 >/dev/null 2>&1; then
    PIP="pip3"
elif command -v pip >/dev/null 2>&1; then
    PIP="pip"
else
    echo "[WARN] 未找到 pip，跳过依赖安装。请手动执行:"
    echo "       pip install -r requirements.txt"
    echo
    echo "安装完成。重启 Agent 后即可使用。"
    exit 0
fi

read -r -p "是否安装 Python 依赖？[y/N] " reply
case "${reply}" in
    [yY]*)
        "${PIP}" install -r "$(dirname "${BASH_SOURCE[0]}")/requirements.txt"
        ;;
    *)
        echo "已跳过。稍后可手动执行: pip install -r requirements.txt"
        ;;
esac

echo
echo "安装完成。重启 Agent 后即可使用。"
echo "试试说：开始写综述：<你的选题>"
