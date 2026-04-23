import os
import sys
import glob
sys.path.append('../')
from setting.setting import *

def get_skills_context(content_limit=3000) -> str:
    """扫描技能目录，读取所有 md 文件，生成技能使用说明上下文，如果没有 md 文件则跳过"""
    if not os.path.exists(skills_path):
        return "当前没有可用的本地技能目录。"

    context_lines = ["以下是当前可用的本地技能及其使用说明（从技能包的 markdown 文件中提取）："]

    # 遍历 skills 下的各个技能包目录
    skill_folders = [f.path for f in os.scandir(skills_path) if f.is_dir()]

    if not skill_folders:
        return "未发现任何技能包。"

    for folder in skill_folders:
        skill_name = os.path.basename(folder)
        # 查找该技能包下的所有 markdown 文件
        md_files = glob.glob(os.path.join(folder, "*.md"))

        # 如果一个都没有没有就 pass
        if not md_files:
            continue
        context_lines.append(f"\n--- 技能包: {skill_name} ---")
        context_lines.append(f"该技能包所在相对路径: {os.path.relpath(folder, ROOT_PATH)}")
        for md_file in md_files:
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        context_lines.append(f"\n[文件: {os.path.basename(md_file)}]")
                        # 截断太长的 md 文件，提取核心说明避免 token 溢出
                        context_lines.append(content[:content_limit])
            except Exception as e:
                context_lines.append(f"读取文件 {os.path.basename(md_file)} 失败: {e}")

    return "\n".join(context_lines)

def get_self_awareness():
    user_md_path = os.path.join(memory_path,'user.md')
    if not os.path.exists(user_md_path):
        return f"请优先引导用户明确双方身份：我方应答角色、用户身份，以及对话风格与交互规则。如果用户确认双方身份,必须最优先记录下用户身份,记录的路径是:{user_md_path}"
    try:
        with open(user_md_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return f"角色定位:{content}"
    except Exception as e:
        os.remove(user_md_path)
        return f"读取用户角色定位错误，请优先引导用户明确双方身份：我方应答角色、用户身份，以及对话风格与交互规则。如果用户确认双方身份,必须最优先记录下用户身份,记录的路径是:{user_md_path}"



# print(get_skills_context())