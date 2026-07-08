#!/usr/bin/env python3
"""
断点续传模块
论文生成过程中自动保存进度，中断后可精确恢复。
"""
import json, os, hashlib
from pathlib import Path
from datetime import datetime

CHECKPOINT_DIR = Path.home() / ".math-model-paper" / "checkpoints"


def ensure_dir():
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)


def session_id(data_file, problem_title):
    """根据输入生成唯一会话ID"""
    h = hashlib.md5(f"{data_file}_{problem_title}".encode()).hexdigest()[:12]
    return f"session_{h}"


def get_checkpoint_path(session_id):
    return CHECKPOINT_DIR / f"{session_id}.json"


def save_checkpoint(session_id, step_name, data, meta=None):
    """保存断点

    Args:
        session_id: 会话ID
        step_name: 步骤名称 (如 'step3_section_4.3', 'step5_round2')
        data: 该步骤的产出数据
        meta: 会话元信息
    """
    ensure_dir()
    path = get_checkpoint_path(session_id)

    checkpoint = {
        "session_id": session_id,
        "updated_at": datetime.now().isoformat(),
        "meta": meta or {},
        "completed_steps": {},
    }

    # 加载已有检查点
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)

    # 保存当前步骤
    checkpoint["completed_steps"][step_name] = {
        "completed_at": datetime.now().isoformat(),
        "data": data,
    }
    checkpoint["updated_at"] = datetime.now().isoformat()

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    return path


def load_checkpoint(session_id):
    """加载断点"""
    path = get_checkpoint_path(session_id)
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_completed_steps(session_id):
    """获取已完成的步骤列表"""
    cp = load_checkpoint(session_id)
    if not cp:
        return []
    return list(cp.get("completed_steps", {}).keys())


def get_next_step(session_id):
    """根据已完成步骤确定下一步"""
    completed = get_completed_steps(session_id)

    # 步骤依赖关系
    step_order = [
        "step1_analyze_data",       # 分析输入数据
        "step2_build_context",      # 建立上下文
        "step2.5_literature",       # 文献检索
        "step3_intro",              # 逐节生成: 引言+问题重述
        "step3_hypothesis",         # 逐节生成: 假设+符号
        "step3_eda",                # 逐节生成: 数据探索
        "step3_model_1",            # 逐节生成: 模型建立(1)
        "step3_model_2",            # 逐节生成: 模型建立(2)
        "step3_diagnostics",        # 逐节生成: 模型诊断
        "step3_evaluation",         # 逐节生成: 模型评价
        "step4_assemble",           # 组装初排
        "step4.5_evidence_check",   # 证据校验
        "step5_dedup_round1",       # 降重第一轮
        "step5_dedup_round2",       # 降重第二轮
        "step5_dedup_round3",       # 降重第三轮
        "step6_deai",               # 去AI味终扫
        "step7_write_docx",         # 写入Word
    ]

    for step in step_order:
        if step not in completed:
            # 找到第一个未完成的步骤
            return step, step_order.index(step), completed

    return None, len(step_order), completed  # 全部完成


def get_checkpoint_summary(session_id):
    """获取断点摘要信息"""
    cp = load_checkpoint(session_id)
    if not cp:
        return None

    steps = cp.get("completed_steps", {})
    sorted_steps = sorted(steps.keys(), key=lambda s: steps[s]["completed_at"])

    summary = {
        "session_id": session_id,
        "total_steps_completed": len(steps),
        "first_step_at": steps[sorted_steps[0]]["completed_at"] if sorted_steps else None,
        "last_step_at": steps[sorted_steps[-1]]["completed_at"] if sorted_steps else None,
        "completed_steps": sorted_steps,
        "next_step": get_next_step(session_id)[0],
        "meta": cp.get("meta", {}),
    }
    return summary


def list_all_sessions():
    """列出所有检查点会话"""
    ensure_dir()
    sessions = []
    for f in CHECKPOINT_DIR.glob("*.json"):
        cp = load_checkpoint(f.stem)
        if cp:
            meta = cp.get("meta", {})
            sessions.append({
                "session_id": f.stem,
                "title": meta.get("title", "未知"),
                "updated": cp.get("updated_at", ""),
                "steps": len(cp.get("completed_steps", {})),
                "competition": meta.get("competition", ""),
            })
    return sorted(sessions, key=lambda s: s["updated"], reverse=True)


def delete_checkpoint(session_id):
    """删除检查点"""
    path = get_checkpoint_path(session_id)
    if path.exists():
        os.remove(path)
        return True
    return False


def resume_prompt(session_id):
    """生成恢复提示"""
    cp = load_checkpoint(session_id)
    if not cp:
        return "未找到检查点。请从头开始生成。"

    next_step, step_idx, completed = get_next_step(session_id)
    meta = cp.get("meta", {})

    prompt = f"""## 断点恢复

会话ID: {session_id}
论文题目: {meta.get('title', '未知')}
竞赛类型: {meta.get('competition', '国赛')}
数据文件: {meta.get('data_file', '未知')}

已完成步骤 ({len(completed)}步):
{chr(10).join(f'  ✅ {s}' for s in completed)}

下一步: {next_step} (第 {step_idx+1}/18 步)

---

我已从断点恢复。请从 **{next_step}** 开始继续生成。
以下是已完成步骤的产出摘要：

"""
    for step_name in completed:
        step_data = cp["completed_steps"].get(step_name, {}).get("data", {})
        if isinstance(step_data, dict) and "text" in step_data:
            preview = step_data["text"][:200] + "..." if len(step_data["text"]) > 200 else step_data["text"]
            prompt += f"\n### {step_name}\n{preview}\n"
        elif isinstance(step_data, dict) and "summary" in step_data:
            prompt += f"\n### {step_name}\n{step_data['summary']}\n"

    return prompt


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='断点续传管理')
    parser.add_argument('action', choices=['list', 'status', 'resume', 'delete', 'clean'],
                        help='操作: list(列出所有), status(查看状态), resume(生成恢复提示), delete(删除), clean(清理所有)')
    parser.add_argument('--session', '-s', default=None, help='会话ID')
    parser.add_argument('--data-file', help='数据文件路径')
    parser.add_argument('--title', help='论文题目')
    parser.add_argument('--step', help='步骤名称')
    parser.add_argument('--data', help='步骤数据(JSON字符串)')
    parser.add_argument('--competition', default='国赛', help='竞赛类型')
    args = parser.parse_args()

    if args.action == 'list':
        sessions = list_all_sessions()
        if not sessions:
            print("无检查点记录。")
        else:
            for s in sessions:
                print(f"  [{s['session_id']}] {s['title']} ({s['competition']}) - {s['steps']}步完成 - {s['updated']}")

    elif args.action == 'status':
        if not args.session:
            print("请指定 --session <id>")
        else:
            summary = get_checkpoint_summary(args.session)
            if summary:
                print(json.dumps(summary, ensure_ascii=False, indent=2))
            else:
                print(f"未找到会话: {args.session}")

    elif args.action == 'resume':
        if not args.session:
            print("请指定 --session <id>")
        else:
            print(resume_prompt(args.session))

    elif args.action == 'save':
        if not all([args.session, args.step, args.data]):
            print("请指定 --session, --step, --data")
        else:
            step_data = json.loads(args.data)
            meta = {"title": args.title or "", "competition": args.competition,
                    "data_file": args.data_file or ""}
            save_checkpoint(args.session, args.step, step_data, meta)
            print(f"检查点已保存: {args.session} -> {args.step}")

    elif args.action == 'delete':
        if not args.session:
            print("请指定 --session <id>")
        else:
            ok = delete_checkpoint(args.session)
            print(f"已删除: {args.session}" if ok else f"未找到: {args.session}")

    elif args.action == 'clean':
        ensure_dir()
        for f in CHECKPOINT_DIR.glob("*.json"):
            os.remove(f)
        print("已清理所有检查点。")
